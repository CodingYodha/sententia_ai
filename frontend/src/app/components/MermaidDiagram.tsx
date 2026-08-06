"use client";

/**
 * MermaidDiagram — Client-side only Mermaid.js renderer
 *
 * Key design decisions:
 * 1. Dynamic import of mermaid at render time — zero backend dependency at render time (FR-5.2)
 * 2. `use client` + useEffect pattern — Mermaid requires DOM, cannot run on server
 * 3. Each diagram gets a unique ID to avoid Mermaid's internal ID conflicts
 * 4. Detects theme from parent (dark/light) and forwards to Mermaid
 * 5. Exposes `svgRef` so the parent can read the rendered SVG for export
 *
 * Export:
 * - PNG: SVG → canvas → PNG blob (canvas API, no external library)
 * - PDF: Browser Print API on isolated SVG (no external library)
 */

import { useEffect, useId, useRef, useState } from "react";

export type DiagramTheme = "dark" | "default" | "forest" | "neutral";

interface MermaidDiagramProps {
  syntax: string;
  theme?: DiagramTheme;
  className?: string;
  onSvgReady?: (svgElement: SVGSVGElement) => void;
}

export function MermaidDiagram({
  syntax,
  theme = "dark",
  className = "",
  onSvgReady,
}: MermaidDiagramProps) {
  const uid = useId().replace(/:/g, "m"); // unique, URL-safe ID
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!syntax?.trim()) return;

    let cancelled = false;

    async function render() {
      setLoading(true);
      setError(null);

      try {
        // Dynamic import — mermaid is a large ESM bundle; load once
        const { default: mermaid } = await import("mermaid");

        mermaid.initialize({
          startOnLoad: false,
          theme,
          securityLevel: "loose", // needed for classDef styling
          fontFamily: "'Inter', 'Segoe UI', sans-serif",
          flowchart: {
            htmlLabels: true,
            curve: "basis",
            rankSpacing: 80,
            nodeSpacing: 60,
          },
        });

        if (cancelled) return;

        const diagramId = `mermaid-${uid}`;
        const { svg } = await mermaid.render(diagramId, syntax);

        if (cancelled) return;

        const container = containerRef.current;
        if (!container) return;
        container.innerHTML = svg;

        // Expose the rendered SVG element to parent (for export) and ensure responsive scaling
        const svgEl = container.querySelector("svg") as SVGSVGElement | null;
        if (svgEl) {
          // Ensure viewBox is set for crisp scaling
          if (!svgEl.getAttribute("viewBox")) {
            const w = parseFloat(svgEl.getAttribute("width") || "800");
            const h = parseFloat(svgEl.getAttribute("height") || "600");
            svgEl.setAttribute("viewBox", `0 0 ${w} ${h}`);
          }
          svgEl.setAttribute("width", "100%");
          svgEl.setAttribute("height", "100%");
          svgEl.style.width = "100%";
          svgEl.style.height = "100%";
          svgEl.style.maxWidth = "100%";
          svgEl.style.maxHeight = "100%";
          svgEl.style.objectFit = "contain";
          svgEl.style.display = "block";
          svgEl.style.margin = "0 auto";

          if (onSvgReady) {
            onSvgReady(svgEl);
          }
        }

        setLoading(false);
      } catch (err) {
        if (!cancelled) {
          const msg = err instanceof Error ? err.message : String(err);
          setError(`Diagram render error: ${msg}`);
          setLoading(false);
        }
      }
    }

    render();
    return () => { cancelled = true; };
  }, [syntax, theme, uid, onSvgReady]);

  if (error) {
    return (
      <div
        className={`rounded-xl p-4 text-sm font-mono ${className}`}
        style={{
          background: "rgba(248,113,113,0.08)",
          border: "1px solid rgba(248,113,113,0.25)",
          color: "#fca5a5",
        }}
      >
        <p className="font-semibold mb-2">⚠ Diagram render error</p>
        <p style={{ color: "#fca5a5", opacity: 0.8 }}>{error}</p>
        <details className="mt-3">
          <summary style={{ cursor: "pointer", opacity: 0.6, fontSize: "0.7rem" }}>
            Raw Mermaid syntax
          </summary>
          <pre
            className="mt-2 overflow-x-auto text-xs"
            style={{ color: "#94a3b8", lineHeight: 1.6 }}
          >
            {syntax}
          </pre>
        </details>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      {loading && (
        <div
          className="absolute inset-0 flex items-center justify-center rounded-xl"
          style={{ background: "rgba(15,18,30,0.6)", zIndex: 10 }}
        >
          <div className="flex items-center gap-3" style={{ color: "#818cf8" }}>
            <svg
              className="animate-spin"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
            <span className="text-sm">Rendering diagram…</span>
          </div>
        </div>
      )}
      <div
        ref={containerRef}
        id={`container-${uid}`}
        className="mermaid-container overflow-x-auto"
        style={{ minHeight: loading ? "200px" : undefined }}
      />
    </div>
  );
}
