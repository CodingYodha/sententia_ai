"""
Sententia.ai — Diagram Serializer

Converts a StructuringAlternative (Prompt 4 output) into valid Mermaid.js graph TD syntax.

Design decisions:
─────────────────
1. TWO-PASS APPROACH:
   Pass 1: Try to validate and reuse the LLM-written mermaid_diagram field.
           The LLM is instructed to produce Mermaid; usually correct, sometimes malformed.
   Pass 2: If Pass 1 fails syntax validation → regenerate from structured fields:
           ownership_chain, jurisdictions_involved, compliance_touchpoints.
   Warnings document which pass was used.

2. NODE TYPES (distinct CSS classes):
   - entityNode      : legal entity (fund, holdco, opco, jv)
   - regulatoryNode  : regulatory-approval checkpoint (DPIIT approval, FIPB, etc.)
   - originNode      : origin investor / UBO (topmost node)
   - targetNode      : target operating company (bottom node)

3. EDGE TYPES:
   - solid -->   : capital flow / equity investment
   - dashed -.-> : regulatory filing / notification
   - dotted ~~~  : passive link / info

4. SYNTAX SAFETY:
   - All node labels are sanitized (quotes, special chars stripped/replaced)
   - Node IDs are slug-ified (alphanumeric + underscore only)
   - Mermaid reserved words avoided in node IDs
   - classDef block always emitted at the end
   - No empty node definitions

5. REGULATORY CHECKPOINTS:
   Compliance touchpoints from ComplianceTouchpoint are inserted as distinct
   diamond nodes ({{...}}) on the relevant edges, styled as regulatoryNode.
   Only pre_signing, pre_closing, and at_closing touchpoints are rendered
   (post_closing and ongoing would clutter the flow diagram).
"""

from __future__ import annotations

import logging
import re
import textwrap
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# CSS CLASS DEFINITIONS (appended to every Mermaid diagram)
# These map to mermaid.js classDef — the frontend renders them with its theme
# ──────────────────────────────────────────────────────────────────────────────
_CLASS_DEFS = """\
    classDef originNode     fill:#f5f5f4,stroke:#292524,color:#0c0a09,stroke-width:2px,rx:8px,ry:8px
    classDef spvNode        fill:#f0fdf4,stroke:#16a34a,color:#14532d,stroke-width:2px,rx:8px,ry:8px
    classDef entityNode     fill:#ffffff,stroke:#78716c,color:#0c0a09,stroke-width:1.5px,rx:8px,ry:8px
    classDef targetNode     fill:#eff6ff,stroke:#2563eb,color:#1e3a8a,stroke-width:2px,rx:8px,ry:8px
    classDef regulatoryNode fill:#fffbeb,stroke:#d97706,color:#78350f,stroke-width:2px,stroke-dasharray:4 2,rx:8px,ry:8px"""

# Mermaid reserved words that cannot be used as node IDs
_RESERVED = frozenset(["end", "graph", "subgraph", "style", "class", "click",
                        "direction", "note", "linkStyle", "classDef"])


# ──────────────────────────────────────────────────────────────────────────────
# INTERNAL INTERMEDIATE REPRESENTATION
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class _Node:
    id: str                    # slug-ified unique ID
    label: str                 # display label (may contain newlines via <br/>)
    node_class: str            # entityNode | originNode | targetNode | regulatoryNode
    shape: str = "rect"        # rect | diamond | stadium | cylinder
    jurisdiction: str = ""


@dataclass
class _Edge:
    from_id: str
    to_id: str
    label: str = ""            # edge annotation (ownership %, flow type)
    style: str = "-->"         # --> | -.-> | ===


@dataclass
class _Diagram:
    nodes: list[_Node] = field(default_factory=list)
    edges: list[_Edge] = field(default_factory=list)
    entity_count: int = 0
    edge_count: int = 0
    regulatory_checkpoint_count: int = 0
    warnings: list[str] = field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _slugify(text: str, prefix: str = "n") -> str:
    """Convert text to a safe Mermaid node ID."""
    slug = re.sub(r"[^a-zA-Z0-9]", "_", text.strip())
    slug = re.sub(r"_+", "_", slug).strip("_").lower()
    if not slug:
        slug = prefix
    if slug[0].isdigit() or slug in _RESERVED:
        slug = f"{prefix}_{slug}"
    return slug[:40]   # cap length


def _safe_label(text: str) -> str:
    """Remove characters that break Mermaid node labels."""
    # Keep labels to plain, single-line text.  Mermaid's unquoted diamond labels
    # interpret parentheses and escaped newlines as syntax tokens.
    text = text.replace('"', "'").replace("`", "'")
    text = re.sub(r"[{}|\[\]]", "", text)
    text = text.replace("\\n", " ")
    return re.sub(r"\s+", " ", text).strip()


def _node_mermaid(node: _Node) -> str:
    """Emit a single Mermaid node definition line."""
    lbl = _safe_label(node.label)
    if node.shape == "diamond":
        return f'    {node.id}{{"{lbl}"}}'
    elif node.shape == "stadium":
        return f'    {node.id}(["{lbl}"])'
    elif node.shape == "cylinder":
        return f'    {node.id}[("{lbl}")]'
    else:
        return f'    {node.id}["{lbl}"]'


def _edge_mermaid(edge: _Edge) -> str:
    """Emit a single Mermaid edge definition line."""
    lbl_part = f"|{_safe_label(edge.label)}|" if edge.label else ""
    return f"    {edge.from_id} {edge.style}{lbl_part} {edge.to_id}"


def _class_mermaid(node: _Node) -> str:
    """Emit a class assignment line."""
    return f"    class {node.id} {node.node_class}"


# ──────────────────────────────────────────────────────────────────────────────
# PASS 1: VALIDATE LLM-WRITTEN MERMAID
# ──────────────────────────────────────────────────────────────────────────────

def _validate_llm_mermaid(raw: str) -> tuple[bool, str]:
    """
    Light structural validation of the LLM-written or simulation template mermaid_diagram string.
    Returns (is_valid, cleaned_string).
    """
    if not raw or not raw.strip():
        return False, ""

    text = raw.strip()

    # Normalize: some LLMs emit ``` mermaid ... ``` fences
    text = re.sub(r"^```\s*mermaid\s*\n?", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()

    # Clean frontmatter if present
    text = re.sub(r"^---[\s\S]*?---\s*", "", text).strip()

    # Must have a graph or flowchart declaration
    if not re.search(r"(?:graph|flowchart)\s+(TD|LR|RL|BT|TB)", text, re.IGNORECASE):
        return False, ""

    # Must have at least one node or subgraph
    if not re.search(r"\w+[\[({]|subgraph", text, re.IGNORECASE):
        return False, ""

    # Must have at least one edge
    if "-->" not in text and "-.->" not in text and "->" not in text:
        return False, ""

    return True, text


def _enrich_llm_mermaid(
    raw: str,
    alternative: dict,
    show_regulatory: bool,
) -> tuple[str, int, int, int, list[str]]:
    """
    Take the (validated) Mermaid string and return it cleanly.
    If subgraphs exist (e.g. USA / INDIA subgraphs in simulation templates), return intact.
    """
    warnings: list[str] = []
    text = raw.strip()
    text = re.sub(r"^---[\s\S]*?---\s*", "", text).strip()

    # Count existing entities and edges
    entity_count = len(re.findall(r"\w+[\[({]", text))
    edge_count = len(re.findall(r"-->|--\||-\.->", text))

    # If diagram already has detailed subgraphs / styling (simulation template), return intact
    if "subgraph" in text.lower():
        return text, entity_count, edge_count, 0, warnings

    checkpoint_count = 0
    touchpoints = alternative.get("compliance_touchpoints", [])

    if show_regulatory and touchpoints:
        checkpoint_lines = []
        class_lines = []
        for i, tp in enumerate(touchpoints):
            timing = tp.get("timing", "ongoing")
            if timing not in ("pre-signing", "pre-closing", "at-closing"):
                continue
            authority = _safe_label(tp.get("authority", "Authority"))
            jurisdiction = _safe_label(tp.get("jurisdiction", ""))
            requirement = _safe_label(tp.get("requirement", "Approval"))[:60]
            node_id = _slugify(f"reg_{i}_{authority}")
            lbl = f"{authority} ({jurisdiction}) {requirement}"
            checkpoint_lines.append(f'    {node_id}{{"{lbl}"}}')
            class_lines.append(f"    class {node_id} regulatoryNode")
            checkpoint_count += 1

        if checkpoint_lines:
            text = text.rstrip()
            text += "\n    %% Regulatory Checkpoints\n"
            text += "\n".join(checkpoint_lines) + "\n"
            text += "\n".join(class_lines) + "\n"

    # Append classDef block if not present
    if "classDef" not in text:
        text = text.rstrip() + "\n" + _CLASS_DEFS + "\n"

    return text, entity_count, edge_count, checkpoint_count, warnings




# ──────────────────────────────────────────────────────────────────────────────
# PASS 2: REGENERATE FROM STRUCTURED FIELDS
# ──────────────────────────────────────────────────────────────────────────────

def _parse_ownership_chain(chain: str) -> list[tuple[str, str, str]]:
    """
    Parse ownership_chain string like:
      'PRC Fund (100%) → Singapore HoldCo (74%) → India OpCo'
    into list of (entity_name, ownership_pct, jurisdiction_hint).
    """
    # Split on → or ->
    parts = re.split(r"\s*(?:→|->)\s*", chain)
    result = []
    for part in parts:
        part = part.strip()
        # Extract pct: "(74%)" or "74%"
        pct_match = re.search(r"\((\d+(?:\.\d+)?%?)\)", part)
        pct = pct_match.group(1) if pct_match else ""
        name = re.sub(r"\s*\(\d+(?:\.\d+)?%?\)\s*", "", part).strip()
        # Try to guess jurisdiction from name
        jurisdiction = ""
        for jkw in ["Singapore", "India", "China", "PRC", "Cayman", "UK", "US",
                     "UAE", "Luxembourg", "France", "Germany", "Mauritius"]:
            if jkw.lower() in name.lower():
                jurisdiction = jkw
                break
        result.append((name, pct, jurisdiction))
    return result


def _build_diagram_from_fields(
    alternative: dict,
    show_regulatory: bool,
    show_flow_labels: bool,
) -> _Diagram:
    """
    Build an intermediate _Diagram from the structured fields of a StructuringAlternative.
    Used when Pass 1 validation fails.
    """
    diagram = _Diagram()
    diagram.warnings.append(
        "Mermaid fallback used — LLM mermaid_diagram was malformed or missing. "
        "Diagram rebuilt from ownership_chain and compliance_touchpoints fields."
    )

    ownership_chain = alternative.get("ownership_chain", "")
    name = alternative.get("name", "Structure")
    jurisdictions = alternative.get("jurisdictions_involved", [])
    touchpoints   = alternative.get("compliance_touchpoints", [])

    entities = _parse_ownership_chain(ownership_chain)
    if len(entities) < 2:
        # Fallback: build simple 2-node from jurisdictions
        juris = jurisdictions or ["Origin", "Target"]
        entities = [(juris[0], "100%", juris[0]), (juris[-1], "", juris[-1])]
        diagram.warnings.append("Ownership chain too short or unparseable — used jurisdictions list.")

    # Classify nodes
    seen_ids: dict[str, str] = {}

    for i, (entity_name, pct, jur_hint) in enumerate(entities):
        node_id = _slugify(entity_name, prefix=f"e{i}")
        # Deduplicate
        if node_id in seen_ids.values():
            node_id = f"{node_id}_{i}"

        if i == 0:
            node_class = "originNode"
            shape = "stadium"
        elif i == len(entities) - 1:
            node_class = "targetNode"
            shape = "rect"
        else:
            node_class = "entityNode"
            shape = "rect"

        # Try to find jurisdiction from jurisdictions_involved
        jur = jur_hint
        if not jur and i < len(jurisdictions):
            jur = jurisdictions[i]

        lbl = entity_name
        if jur and jur.lower() not in entity_name.lower():
            lbl = f"{entity_name}\\n[{jur}]"

        node = _Node(id=node_id, label=lbl, node_class=node_class, shape=shape, jurisdiction=jur)
        diagram.nodes.append(node)
        seen_ids[entity_name] = node_id

    # Build edges from the ownership chain
    for i in range(len(diagram.nodes) - 1):
        from_node = diagram.nodes[i]
        to_node   = diagram.nodes[i + 1]
        _, pct, _ = entities[i + 1]
        lbl = ""
        if show_flow_labels and pct:
            lbl = f"Capital / {pct} equity"
        diagram.edges.append(_Edge(
            from_id=from_node.id,
            to_id=to_node.id,
            label=lbl,
            style="-->",
        ))

    diagram.entity_count = len(diagram.nodes)
    diagram.edge_count   = len(diagram.edges)

    # Add regulatory checkpoint nodes
    if show_regulatory:
        for i, tp in enumerate(touchpoints):
            timing = tp.get("timing", "ongoing")
            if timing not in ("pre-signing", "pre-closing", "at-closing"):
                continue
            authority    = _safe_label(tp.get("authority", "Authority"))
            jurisdiction = _safe_label(tp.get("jurisdiction", ""))
            requirement  = _safe_label(tp.get("requirement", "Approval"))[:60]
            node_id = _slugify(f"reg_{i}_{authority}")
            lbl = f"{authority} ({jurisdiction}) {requirement}"
            diagram.nodes.append(_Node(
                id=node_id,
                label=lbl,
                node_class="regulatoryNode",
                shape="diamond",
            ))
            diagram.regulatory_checkpoint_count += 1

    return diagram


# ──────────────────────────────────────────────────────────────────────────────
# RENDERER: _Diagram → Mermaid string
# ──────────────────────────────────────────────────────────────────────────────

def _render_diagram(diagram: _Diagram) -> str:
    """Render the intermediate _Diagram into a Mermaid graph TD string."""
    lines = ["graph TD"]

    # Nodes
    for node in diagram.nodes:
        lines.append(_node_mermaid(node))

    # Blank line
    lines.append("")

    # Edges
    for edge in diagram.edges:
        lines.append(_edge_mermaid(edge))

    # Blank line
    lines.append("")

    # Class assignments
    for node in diagram.nodes:
        lines.append(_class_mermaid(node))

    # classDef block
    lines.append("")
    lines.append(_CLASS_DEFS)

    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

def serialize_structure_to_mermaid(
    alternative: dict[str, Any],
    show_regulatory_checkpoints: bool = True,
    show_capital_flow_labels: bool = True,
) -> tuple[str, int, int, int, list[str]]:
    """
    Convert a StructuringAlternative dict into Mermaid.js graph TD syntax.
    If mermaid_diagram is already provided (e.g. from simulation_template_folder),
    normalize syntax and return it directly.
    """
    warnings: list[str] = []
    raw_mermaid = alternative.get("mermaid_diagram", "")

    if raw_mermaid and raw_mermaid.strip():
        # Clean frontmatter & normalize non-standard dotted syntax
        cleaned = re.sub(r"^---[\s\S]*?---\s*", "", raw_mermaid.strip()).strip()
        cleaned = re.sub(r'-\.\s*"([^"]+)"\s*\.-\s*>', r'-.-|"\1"|', cleaned)
        cleaned = re.sub(r'-\.\s*"([^"]+)"\s*\.->', r'-.-|"\1"|', cleaned)

        is_valid, _ = _validate_llm_mermaid(cleaned)
        if is_valid or "subgraph" in cleaned.lower():
            mermaid, entity_count, edge_count, checkpoint_count, w = _enrich_llm_mermaid(
                cleaned, alternative, show_regulatory_checkpoints
            )
            warnings.extend(w)
            logger.info(
                f"Diagram: Preserved exact template/LLM diagram. "
                f"entities={entity_count} edges={edge_count}"
            )
            return mermaid, entity_count, edge_count, checkpoint_count, warnings

    # ── Pass 2: Regenerate from structured fields if no valid raw diagram ──────
    logger.info("Diagram: Running Pass 2 (field-based regeneration)")
    diagram = _build_diagram_from_fields(
        alternative,
        show_regulatory=show_regulatory_checkpoints,
        show_flow_labels=show_capital_flow_labels,
    )

    warnings.extend(diagram.warnings)
    mermaid = _render_diagram(diagram)

    return (
        mermaid,
        diagram.entity_count,
        diagram.edge_count,
        diagram.regulatory_checkpoint_count,
        warnings,
    )


def validate_mermaid_syntax(mermaid: str) -> tuple[bool, str]:
    """
    Public wrapper around Pass 1 validation.
    Returns (is_valid, reason_if_invalid).
    Used by tests.
    """
    valid, cleaned = _validate_llm_mermaid(mermaid)
    if not valid:
        return False, "Missing graph direction, node definitions, or edge definitions"
    return True, ""
