# Sententia.ai — MVP Build Plan
**Zero-cost stack | Demo must survive unscripted, on-the-spot questions**

Not anchored to the PRD's single illustrative example (China → Singapore → India). That case is useful as *one* seed corridor, not the whole demo — see §0 and §4 for why treating it as "the" rehearsed case is a trap.

---

## 0. The one design rule everything else depends on

Two separate engines. Do not merge them.

| Engine | Job | Runs dynamically on any input? |
|---|---|---|
| **Structure Generation** | Propose 2–4 investment structures for whatever scenario is entered | **Yes, always** |
| **Compliance Validation** | Check a structure against real regulatory rules | Only for a **configurable set** of pre-validated corridors. Everything else routes to a labeled LLM-fallback. |

Why this split matters: an LLM's general knowledge of SPVs, holding-company layering, and treaty shopping generalizes across jurisdictions reasonably well — structure generation can be genuinely dynamic. Statutory accuracy does **not** generalize — a model guessing at Vietnamese FDI thresholds is a liability, not a feature. So generation stays live for every query; validation forks between "verified" and "illustrative." That fork is the only place a fallback banner should ever appear.

**Don't hardcode just the PRD's one worked example.** A single rehearsed corridor is trivially spotted as staged the moment anyone tests a second one. Seed the rule engine with 2–3 diverse corridors instead (e.g. one APAC-inbound, one US-outbound, one EU-inbound) so the "verified" path reads as real coverage, not a script — see §4 and §5 for how to keep the set genuinely configurable.

---

## 1. Architecture

```
Frontend: Cloudflare Pages (Next.js)
  │
  ├──► Supabase (Postgres + Auth) — scenarios, users, audit log
  └──► Mermaid.js (client-side) — capital-flow diagram rendering

Backend: Hugging Face Spaces (FastAPI, Docker, 16GB RAM)
  │
  ├──► Docling + Instructor — parse uploaded deal docs into structured JSON
  ├──► Structure Generation Engine — RAG (Qdrant) + LLM, ALWAYS dynamic
  ├──► Gatekeeper Router
  │     ├── match → Open Policy Agent (Rego rules) — configured corridor set
  │     └── no match → RAG + LLM fallback — labeled "illustrative"
  └──► LLM routing: Nemotron 3 (OpenRouter, primary) → Groq/Llama (secondary) → other OpenRouter free models (insurance)

Embeddings: Jina Embeddings API (primary) → Google text-embedding-004 (backup)
```

---

## 2. Infrastructure Stack (all free tier, no card required unless noted)

| Layer | Tool | Link | Free tier | Notes |
|---|---|---|---|---|
| Frontend hosting | Cloudflare Pages | https://pages.cloudflare.com/ | Unlimited bandwidth, 500 builds/mo | No commercial-use restriction, unlike Vercel Hobby |
| Backend hosting | Hugging Face Spaces | https://huggingface.co/spaces | 2 vCPU / 16GB RAM (FastAPI Docker) | Enough RAM for Docling/PyMuPDF; ~30s wake if idle |
| Backend alt | Render | https://render.com/ | 0.5 CPU / 512MB | Fallback only — RAM too tight for doc parsing |
| LLM (primary) | OpenRouter — NVIDIA Nemotron 3 Ultra (free) | openrouter.ai | $0/M tokens, 1M ctx | [Certain] Free-listed on OpenRouter; strong multi-step reasoning, good fit for structuring logic |
| LLM (secondary) | Groq Cloud — Llama 3.3 70B | https://groq.com/ | 30 RPM, 14,400 req/day | Very low latency, good live-demo insurance |
| LLM (tertiary insurance) | Other OpenRouter free models (Nemotron 3 Super, Ling-3.0-flash) | openrouter.ai | $0/M tokens, varies by model | Swap-in if the primary model specifically is congested — provider-level redundancy, see §4 |
| Embeddings (primary) | Jina Embeddings API | https://jina.ai/embeddings/ | [Certain, per current pricing pages] ~1M free tokens on signup (non-commercial), then Free tier 100 RPM / 100K TPM | Confirm non-commercial vs. commercial terms before demo day — fine for a pitch, flag before any paid pilot |
| Embeddings (backup) | Google text-embedding-004 | https://aistudio.google.com/ | 1,500 req/day | [Likely] Google has been tightening Gemini API key policies through 2026 (unrestricted keys blocked June 19, standard keys retiring Sept 2026) — usable, but expect extra setup friction getting a working key fast |
| Vector DB | Qdrant Cloud | https://qdrant.tech/ | 1GB cluster, always-on | Supports payload filtering by jurisdiction — useful for corridor tagging |
| Vector DB (alt) | Pinecone | https://pinecone.io/ | 100K vectors | Fine alternative, slightly less filtering control |
| Relational DB + Auth | Supabase | https://supabase.com/ | 500MB DB, 50K MAU | Pauses after 7 days idle — ping it before the meeting |
| Relational DB (alt) | Neon | https://neon.tech/ | 0.5GB, branch-based | Cold start ~1-2s |
| Diagram rendering | Mermaid.js | https://mermaid.js.org/ | Free, client-side | Zero network dependency — most reliable choice for live demo |
| Diagram (backup) | Kroki.io / viz-js | https://kroki.io/ / https://viz-js.com/ | Free | Only if you need server-side rendering fallback |

---

## 3. Open-source repos to fork (not build from scratch)

| Module | Repo | License / Activity | Adaptation for the demo |
|---|---|---|---|
| Legal RAG pipeline | https://github.com/infiniflow/ragflow | Apache-2.0, 86k★, active | Ingest regulatory material for each corridor in your configured set, plus general structuring/treaty reference material so unrehearsed queries have something real to retrieve against (see §4) |
| Doc intake / extraction | https://github.com/DS4SD/docling | MIT, 48k★ | Parse uploaded cap tables, SHAs, ownership charts into text/tables |
| Structured output validation | https://github.com/jxnl/instructor | MIT, 13.7k★ | Force LLM output into Pydantic schemas (equity %, control rights, jurisdiction) |
| Compliance rule engine | https://github.com/open-policy-agent/opa | Apache-2.0, CNCF graduated | Rego rules for Press Note 3 (2020) / Press Note 2 (2026), Section 9(1)(i), SBO Companies Act |
| Diagram generator | https://github.com/mermaid-js/mermaid | MIT, 70k★ | Python serializer: structured JSON → Mermaid `graph TD` syntax |
| Optional stretch — research synthesis | https://github.com/stanford-oval/storm | MIT, academic | Only if time allows — multi-perspective research drafting for the "why this structure" rationale text |

---

## 4. Structure Generation — the part that must survive live testing

This is the component the investor will actually stress-test. Three things make it robust instead of brittle:

**a) Broaden the RAG corpus beyond any single jurisdiction.**
Don't index only the statutes for whichever corridors you've hardcoded rules for. Also ingest a small general-reference set: OECD Model Tax Convention commentary, a short summary of CFIUS (US), the EU FDI Screening Regulation, MAS's general approach (Singapore), and basic treaty-shopping / GAAR concepts. This gives the retrieval step *something real to ground on* for any jurisdiction pair a live tester throws at it, instead of the LLM answering from pure parametric memory. The broader and more jurisdiction-diverse this corpus is, the less the demo depends on any one rehearsed case.

**b) Few-shot the reasoning pattern, not the facts.**
Use the PRD's worked example (Section 6 — HSG/China → Singapore SPV → India, Primary + Alternative structures) as *one* one-shot exemplar in the system prompt — not the only one. Add a second exemplar from a different region if you can (even a made-up but plausible one). The point isn't the specific facts — it's teaching the model the *shape* of good output: layered vs. direct structure, ownership-split rationale, governance/veto-rights language, citation style. A model that has internalized that shape across more than one example generalizes it to a genuinely new corridor far better than one anchored to a single template.

**c) Model routing for resilience.**
Free-tier LLMs all have caps that a live, simultaneous-testing room can exhaust. Chain: **Nemotron 3 Ultra (OpenRouter, primary) → Groq/Llama 3.3 70B (secondary) → other OpenRouter free models (tertiary insurance)**:

| Model | Context | Notes |
|---|---|---|
| NVIDIA Nemotron 3 Ultra (free, via OpenRouter) | 1M tokens | Primary — strong multi-step reasoning, good match for structuring logic |
| Groq — Llama 3.3 70B (free) | — | Secondary — very low latency, different provider so it survives an OpenRouter-side outage or rate limit |
| NVIDIA Nemotron 3 Super (free, via OpenRouter) | 262K tokens | Tertiary — faster/cheaper, still strong reasoning |
| Ling-3.0-flash (free, via OpenRouter) | 262K tokens | Tertiary — token-efficient, good latency |

Implement this as a simple try/except cascade in the backend — if one provider 429s, fall through automatically. This is the single highest-leverage thing to build for live-demo safety, separate from anything compliance-related.

---

## 5. Compliance Validation — Gatekeeper Proxy

```python
from typing import Dict, Any
import requests

# Pre-validated corridor set — extend this, don't leave it as one entry.
PRE_VALIDATED_CORRIDORS = {
    ("CHINA", "SINGAPORE", "INDIA"),      # PRD's illustrative example — one seed, not the whole set
    ("UNITED STATES", "DELAWARE", "GERMANY"),  # example second corridor
    ("UNITED ARAB EMIRATES", "SINGAPORE", "INDIA"),  # example third corridor
}

def evaluate_compliance_request(payload: Dict[str, Any]) -> Dict[str, Any]:
    origin = payload.get("origin_jurisdiction", "").upper()
    spv = payload.get("spv_jurisdiction", "").upper()
    target = payload.get("target_jurisdiction", "").upper()
    corridor_key = (origin, spv, target)

    if corridor_key in PRE_VALIDATED_CORRIDORS:
        opa_response = requests.post(
            "http://localhost:8181/v1/data/sententia/compliance",
            json={"input": payload}
        )
        return {
            "execution_layer": "DETERMINISTIC_RULE_ENGINE",
            "is_rule_validated": True,
            "ui_banner": None,
            "data": opa_response.json().get("result", {})
        }
    else:
        return {
            "execution_layer": "LLM_FALLBACK_REASONING",
            "is_rule_validated": False,
            "ui_banner": {
                "type": "WARNING",
                "label": "Illustrative — Not Yet Rule-Validated",
                "message": f"Corridor {origin} → {spv} → {target} is operating in "
                           f"fallback mode. Structural reasoning applied via RAG legal corpus."
            },
            "data": run_rag_llm_fallback(payload)
        }
```

Rego rules to encode per corridor in the set — for the India-leg example: Press Note 3 (2020) / Press Note 2 (2026) land-border UBO thresholds, Section 9(1)(i) indirect-transfer tax test, Significant Beneficial Ownership (Companies Act §90) disclosure trigger. Each additional corridor needs its own small rule set — budget real time for this per corridor, it's the part that can't be shortcut.

**Frontend behavior:** when `is_rule_validated: false`, render a visible amber banner ("Illustrative — Not Yet Rule-Validated") above the output. This turns an off-script answer into a visibly intentional fallback mode rather than a failure — practice narrating this line in the demo; it's a feature, not a caught-out moment.

---

## 6. Day-by-day roadmap (5 working days)

| Day | Focus | Deliverable |
|---|---|---|
| 1 | Infra init | Cloudflare Pages + HF Spaces deployed; Supabase + Qdrant provisioned; API keys for OpenRouter/Groq/Jina issued |
| 2 | Intake + extraction | Docling + Instructor pipeline: PDF upload → structured JSON (UBO, equity %, control rights) |
| 3 | Structure generation + compliance gatekeeper | Dynamic generation engine live for any input; OPA rules written for each corridor in the pre-validated set (§0); fallback router wired with banner |
| 4 | Diagrams + resilience | Mermaid.js renderer; LLM provider cascade (Nemotron→Groq→OpenRouter fallback pool) tested under simulated rate-limit failure |
| 5 | Integration + stress test | Full run across every pre-validated corridor; run 3-4 corridors outside the set yourself to confirm fallback output reads as sane, not broken |

---

## 7. Demo rehearsal checklist

- Run every corridor in your pre-validated set until the deterministic-engine output is flawless and fast on each one — not just the PRD's example.
- Before the meeting, personally test 3-4 plausible "surprise" corridors outside the set (e.g. US → Cayman → Vietnam, Germany → Mauritius → Indonesia, generic Delaware PE fund → EU target) so you've already seen what the fallback produces — you should never be surprised by your own system in the room.
- Practice narrating the amber "Illustrative" banner out loud once, so it lands as a designed safeguard, not an apology.
- Have a phone hotspot or backup connection — free-tier infra (HF Spaces wake time, Supabase idle-pause) is the most likely failure point, not the AI logic.

---

## 8. What not to claim in the room

- This is a demo proxy, not the PRD's real compliance engine (that requires a licensed, versioned, multi-jurisdiction knowledge base plus actual lawyer sign-off — Sections 8.4, 8.6, 12 of the PRD).
- The LLM fallback for corridors outside the pre-validated set is directionally reasonable, not legally validated — never present it as reviewed or production-grade.
- Free-tier LLM calls can rate-limit under concurrent load; the provider cascade in §4 is insurance, not a guarantee — test it failing gracefully (a clean message, not a crash) as part of Day 4.
- Jina's free embedding quota is non-commercial by its own terms — fine for a pitch demo, but don't carry that same key into a paid pilot without checking Jina's commercial pricing first.

---

## Appendix — all links

- Frontend: https://pages.cloudflare.com/ · https://www.netlify.com/ · https://vercel.com/
- Backend: https://huggingface.co/spaces · https://render.com/ · https://puter.com/
- LLM APIs: openrouter.ai (Nemotron 3 Ultra/Super, Ling-3.0-flash — free models) · https://groq.com/ · https://together.ai/
- Embeddings: https://jina.ai/embeddings/ (primary) · https://aistudio.google.com/ (backup) · https://cohere.com/
- Vector DB: https://qdrant.tech/ · https://pinecone.io/ · https://supabase.com/ (pgvector)
- Relational DB: https://supabase.com/ · https://neon.tech/ · https://turso.tech/
- Diagrams: https://mermaid.js.org/ · https://kroki.io/ · https://viz-js.com/
- Repos: https://github.com/infiniflow/ragflow · https://github.com/DS4SD/docling · https://github.com/jxnl/instructor · https://github.com/open-policy-agent/opa · https://github.com/mermaid-js/mermaid · https://github.com/stanford-oval/storm
