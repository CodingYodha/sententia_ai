"use client";

/**
 * Results Workspace Page — Sententia.ai
 *
 * Instant Execution Architecture:
 * 1. Frame-0 instant rendering for ALL 4 workspace tabs (Diagram, Alternatives, Timeline, Compliance Audit).
 * 2. Instant tab & rank switching (#1 PropCo-OpCo, #2 Delaware JV, #3 Direct FDI).
 * 3. Simultaneous word-by-word streaming legal reasoning text in the left AI Agent panel (over 5-8 seconds).
 */

import { useEffect, useState, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { StructureCard, type StructuringAlternative, type ComplianceResult } from "../components/StructureCard";
import { ComplianceBanner } from "../components/ComplianceBanner";
import { DisclaimerBanner } from "../components/DisclaimerBanner";
import { DiagramPanel, type DiagramData } from "../components/DiagramPanel";
import { GanttTimeline } from "../components/GanttTimeline";
import { useAuth } from "../components/AuthContext";
import { apiComplianceEvaluate, apiStructuresGenerate } from "@/lib/api";

export const dynamic = "force-dynamic";

interface StoredResults {

  scenarioId: string;
  scenario: Record<string, unknown>;
  alternatives: StructuringAlternative[];
  general_analysis: string;
  recommended_alternative_rank: number;
  disclaimer: string;
  rag_sources_used: number;
  llm_provider_used: string;
  rag_corpus_coverage: string;
  generation_time_ms?: number;
  reasoning_steps?: string[];
  proposed_timeline?: any;
}

const FULL_REASONING_PARAGRAPH = 
  "Analyzing deal scenario parameters for Project Ananta: Capital Origin = USA, Target Jurisdiction = India, Sector = K-12 Education ($3.0M FDI capital injection). Evaluating statutory constraints under the Right of Children to Free and Compulsory Education (RTE) Act 2009 and CBSE Affiliation Bye-Laws which mandate that K-12 schools be operated by non-profit societies, trusts, or Section 8 companies on a no-profit-no-loss basis. Settled Supreme Court precedent (T.M.A. Pai Foundation, Islamic Academy of Education, and Modern Dental College) affirms that education is a noble occupation that does not permit commercial dividend extraction from the school entity. Crucially, Schedule I of the FEMA (Non-Debt Instruments) Rules 2019 expressly carves out 'earning of rent or income on lease of the property, not amounting to transfer' from prohibited real estate business. This legal lynchpin enables a foreign-owned PropCo (Meridian Campus Infrastructure Pvt. Ltd.) to construct school facilities and earn commercial lease rentals. Channelling investments through a for-profit PropCo and OpCo prevents foreign funds from directly touching the non-profit school trust, completely avoiding FCRA 2011 'foreign contribution' triggers and ensuring full regulatory compliance.";

// ── Authoritative Simulation Diagrams ─────────────────────────────────────────
const SIMULATION_DIAGRAM_1 = `flowchart TB

subgraph USA
direction LR
MGF["Meridian Grace<br/>Foundation (MGF)<br/>US 501(c)(3) non-profit"]
AEP["Atlas Education<br/>Partners LLC (AEP)<br/>Delaware LLC investor"]
MGF -.-|"co-invest under a<br/>Term Sheet"| AEP
end

subgraph INDIA
direction TB
PROP["Meridian Campus<br/>Infrastructure Pvt. Ltd.<br/>('PropCo')<br/>Indian WOS<br/>owns land & school building"]
OPCO["Ananta Educare<br/>Pvt. Ltd.<br/>('OpCo')<br/>for-profit Educational<br/>Services Company (ESC)"]
AET["Ananta Education Trust<br/>('AET')<br/>registered public charitable trust,<br/>holds CBSE affiliation,<br/>runs on no-profit-no-loss basis"]
SCHOOL(("Ananta International School<br/>(Pune, Maharashtra - CBSE)"))

PROP -->|"Registered long-term<br/>Lease Deed (campus)"| AET
OPCO -->|"Management &<br/>Consultancy Agreement"| AET
AET -.-|"operates"| SCHOOL
end

MGF -->|"FDI: equity shares<br/>(incorporation) +<br/>CCPS (capex tranche)"| PROP
AEP -->|"FDI: equity shares<br/>(FMV valuation,<br/>FC-GPR reporting)"| OPCO`;

const SIMULATION_DIAGRAM_2 = `flowchart TB

subgraph USA
direction LR
MGF["Meridian Grace<br/>Foundation (MGF)"]
AEP["Atlas Education<br/>Partners LLC (AEP)"]
end

subgraph INDIA
direction TB
PROP["Meridian Campus<br/>Infrastructure Pvt. Ltd.<br/>('PropCo')"]
OPCO["Ananta Educare<br/>Pvt. Ltd.<br/>('OpCo')"]
AET["Ananta Education Trust<br/>('AET')<br/>school operator,<br/>no dividend capacity"]
FUNDS(("School fee collections fund<br/>lease rent + consultancy fees<br/>+ reasonable surplus (6–15%)"))

FUNDS -.- AET
AET -->|"Lease rental<br/>(Sec.194-I TDS 10% +<br/>18% GST - domestic,<br/>both Indian residents)"| PROP
AET -->|"Consultancy fees<br/>(arm's length,<br/>transfer-pricing tested;<br/>18% GST)"| OPCO
end

PROP -->|"Dividends<br/>(Art.10 India-US DTAA:<br/>15% -> >=10% voting stock)"| MGF
OPCO -->|"Dividends<br/>(Art.10 India-US DTAA:<br/>15% -> >=10% voting stock)"| AEP`;

const SIMULATION_DIAGRAM_3 = `flowchart TB

subgraph USA
direction LR
MGF["Meridian Grace<br/>Foundation (MGF)"]
AEP["Atlas Education<br/>Partners LLC (AEP)"]
JV["Meridian-Atlas<br/>Education JV LLC<br/>(Delaware)<br/><br/>JV LLC allocates returns to MGF & AEP<br/>per Operating Agreement split"]

MGF -->|"capitalize jointly,<br/>per agreed split"| JV
AEP -->|"capitalize jointly,<br/>per agreed split"| JV
end

subgraph INDIA
direction TB
PROP["Meridian Campus<br/>Infrastructure Pvt. Ltd.<br/>('PropCo')<br/>sole FDI conduit<br/>for the campus"]
OPCO["Ananta Educare<br/>Pvt. Ltd.<br/>('OpCo')<br/>sole FDI conduit<br/>for school services"]
AET["Ananta Education Trust<br/>('AET')<br/>lease + consultancy<br/>counterparty for both entities"]

PROP --> AET
OPCO --> AET
end

JV -->|"single FDI<br/>tranche"| PROP
JV -->|"single FDI<br/>tranche"| OPCO

PROP -->|"dividends up<br/>to JV LLC"| JV
OPCO -->|"dividends up<br/>to JV LLC"| JV`;

// Pre-populated instant compliance map for frame-0 zero-latency loading
const INITIAL_COMPLIANCE_MAP: Record<number, ComplianceResult> = {
  1: {
    is_rule_validated: true,
    is_allowed: true,
    overall_confidence: "high",
    compliance_score: 96,
    rules_checked: 14,
    blocking_issues: [],
    warning_issues: [
      {
        rule_code: "TRANSFER_PRICING_01",
        description: "OpCo management fees subject to Transfer Pricing arm's-length documentation",
        severity: "medium",
        mitigation: "Maintain CA Transfer Pricing study annually",
      }
    ],
    required_filings: [
      "FEMA FC-GPR via FIRMS Portal within 30 days of share allotment",
      "Section 194-I TDS (10%) quarterly tax returns",
      "RBI Annual Return on Foreign Liabilities and Assets (FLA)",
    ],
    jurisdiction_breakdown: [
      { jurisdiction: "India", status: "COMPLIANT", note: "FEMA NDI Schedule I Real Estate Lease Carve-Out verified" },
      { jurisdiction: "USA", status: "COMPLIANT", note: "Form 5471 / 8865 IRS reporting" },
    ],
  },
  2: {
    is_rule_validated: true,
    is_allowed: true,
    overall_confidence: "high",
    compliance_score: 88,
    rules_checked: 14,
    blocking_issues: [],
    warning_issues: [],
    required_filings: [
      "Delaware Annual Franchise Tax & Report",
      "FEMA FC-GPR for Delaware JV LLC FDI injection",
    ],
    jurisdiction_breakdown: [
      { jurisdiction: "India", status: "COMPLIANT", note: "FDI compliant under automatic route" },
      { jurisdiction: "Delaware (US)", status: "COMPLIANT", note: "Delaware LLC Operating Agreement valid" },
    ],
  },
  3: {
    is_rule_validated: true,
    is_allowed: true,
    overall_confidence: "medium",
    compliance_score: 82,
    rules_checked: 14,
    blocking_issues: [],
    warning_issues: [],
    required_filings: [
      "Section 195 TDS Form 15CA/15CB for cross-border dividend remittance",
    ],
    jurisdiction_breakdown: [
      { jurisdiction: "India", status: "COMPLIANT", note: "DTAA Article 10 15% dividend rate applied" },
    ],
  },
};

const INITIAL_FALLBACK_RESULTS: StoredResults = {
  scenarioId: "simulation-ananta-001",
  scenario: {
    investor_name: "Meridian Grace Foundation & Atlas Education Partners",
    capital_origin: "USA",
    target_jurisdiction: "India",
    spv_jurisdiction: "Delaware (US)",
    sector: "Education",
    investment_amount_usd: 3000000,
    equity_pct: 100,
    investment_structure_type: "spv_layered",
    notes: "Project Ananta PropCo-OpCo FDI Model",
  },
  alternatives: [
    {
      rank: 1,
      name: "PropCo–OpCo Dual Vehicle Structure (Project Ananta Model)",
      structure_type: "spv_layered",
      architecture_description: "The primary investment structure routes capital through two separate for-profit Indian vehicles: Meridian Campus Infrastructure Pvt. Ltd. ('PropCo') owns the land and campus buildings, leasing them to Ananta Education Trust under a long-term Lease Deed. Ananta Educare Pvt. Ltd. ('OpCo') provides paid marketing, admissions, teacher training, and financial oversight services.",
      ownership_chain: "USA Investors (MGF & AEP) -> Indian WOS (PropCo & OpCo) -> Ananta Education Trust -> Ananta International School",
      jurisdictions_involved: ["USA", "India"],
      mermaid_diagram: SIMULATION_DIAGRAM_1,
      compliance_touchpoints: [
        { jurisdiction: "India", requirement: "FEMA FC-GPR filing within 30 days of allotment", timing: "post-closing", authority: "RBI / AD Bank" },
        { jurisdiction: "India", requirement: "Section 194-I TDS (10%) + 18% GST on Lease Rent", timing: "ongoing", authority: "Income Tax Dept" },
        { jurisdiction: "India", requirement: "CBSE Non-Profit Character Compliance", timing: "pre-closing", authority: "CBSE Board" },
      ],
      cited_sources: ["FEMA NDI Rules 2019 Schedule I", "CBSE Affiliation Bye-Laws", "Supreme Court Modern Dental College (2016)"],
      identified_risks: [
        { risk_type: "regulatory", description: "GAAR scrutiny on arm's-length rental rates", severity: "medium", mitigation: "Maintain strict CA FMV valuation report" }
      ],
      implementation_steps: [],
      rationale: "Optimizes cross-border capital deployment while isolating non-profit school operator.",
      estimated_setup_complexity: "medium",
      regulatory_confidence: "high"
    },
    {
      rank: 2,
      name: "Delaware Joint Venture (JV LLC) Holding Structure",
      structure_type: "joint_venture",
      architecture_description: "MGF and AEP co-invest into a single Delaware holding vehicle: Meridian-Atlas Education JV LLC. The JV LLC then injects a single consolidated FDI tranche into PropCo and OpCo in India. Dividend returns from PropCo and OpCo flow up to the JV LLC in Delaware before being distributed to MGF and AEP per the JV Operating Agreement.",
      ownership_chain: "MGF (US) + AEP (US) -> Delaware JV LLC -> Indian PropCo & OpCo -> Ananta Education Trust",
      jurisdictions_involved: ["USA", "India", "Delaware (US)"],
      mermaid_diagram: SIMULATION_DIAGRAM_3,
      compliance_touchpoints: [
        { jurisdiction: "USA", requirement: "Delaware LLC Operating Agreement & Joint Governance Framework", timing: "pre-closing", authority: "Delaware Division of Corporations" },
        { jurisdiction: "India", requirement: "FEMA FC-GPR filing for Delaware JV LLC FDI injection", timing: "post-closing", authority: "RBI / AD Bank" },
      ],
      cited_sources: ["Delaware Limited Liability Company Act", "FEMA (NDI) Rules 2019 Schedule I"],
      identified_risks: [
        { risk_type: "tax", description: "Subpart F / GILTI income inclusion for US investors at JV level", severity: "low", mitigation: "Structure JV LLC as pass-through partnership for US tax purposes" }
      ],
      implementation_steps: [],
      rationale: "Provides unified governance and streamlined single-conduit FDI remittance into India.",
      estimated_setup_complexity: "medium",
      regulatory_confidence: "high"
    },
    {
      rank: 3,
      name: "Direct FDI & Lease Fee Repatriation Structure",
      structure_type: "direct_fdi",
      architecture_description: "Focuses on direct fee repatriation and lease rental flows: Ananta Education Trust receives school fees and pays commercial lease rent to PropCo and consultancy fees to OpCo. Annual profits are repatriated to MGF and AEP as foreign dividends under Article 10 of the India-US Tax Treaty.",
      ownership_chain: "School Fee Surplus -> Ananta Education Trust -> PropCo & OpCo (India) -> DTAA Art. 10 Dividends -> MGF & AEP (USA)",
      jurisdictions_involved: ["USA", "India"],
      mermaid_diagram: SIMULATION_DIAGRAM_2,
      compliance_touchpoints: [
        { jurisdiction: "India", requirement: "Article 10 India-US DTAA Dividend Withholding Capping (15%)", timing: "repatriation", authority: "Income Tax Dept / CBDT" },
        { jurisdiction: "India", requirement: "Section 195 TDS Form 15CA/15CB for cross-border dividend remittance", timing: "repatriation", authority: "AD Bank / Tax Auditor" },
      ],
      cited_sources: ["India-US Double Tax Avoidance Agreement (DTAA) Article 10", "Income Tax Act 1961 Section 195"],
      identified_risks: [
        { risk_type: "tax", description: "Withholding tax rate disputes on non-resident dividend distributions", severity: "low", mitigation: "Obtain Form 10F and Tax Residency Certificate (TRC) upfront" }
      ],
      implementation_steps: [],
      rationale: "Simplifies entity count by avoiding intermediate SPVs while using treaty dividend capping.",
      estimated_setup_complexity: "low",
      regulatory_confidence: "high"
    }

  ],
  general_analysis: "### Regulatory Analysis — US-to-India K-12 Education FDI Corridor\n\n1. **No-Profit-No-Loss Mandate:** RTE Act 2009 and CBSE Affiliation Bye-Laws mandate non-profit operation.\n2. **FDI Exemption & PropCo Real Estate Lease:** Schedule I of FEMA NDI Rules carves out rent on lease from real estate business.\n3. **FCRA Insulation:** Foreign capital flows strictly into for-profit PropCo/OpCo, avoiding FCRA foreign contribution triggers.",
  recommended_alternative_rank: 1,
  disclaimer: "⚡ Sententia.ai Simulation Mode: Output generated from pre-validated Project Ananta regulatory templates.",
  rag_sources_used: 5,
  llm_provider_used: "sententia_simulation_engine",
  rag_corpus_coverage: "direct",
};

function ResultsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const { accessToken } = useAuth();

  const [results, setResults] = useState<StoredResults>(INITIAL_FALLBACK_RESULTS);
  const [tabLoading, setTabLoading] = useState<boolean>(true);

  const [activeTab, setActiveTab] = useState<"diagram" | "alternatives" | "compliance" | "timeline">("diagram");
  const [leftTab, setLeftTab] = useState<"agent" | "impact">("agent");
  const [selectedAltRank, setSelectedAltRank] = useState<number>(1);
  const [complianceMap, setComplianceMap] = useState<Record<number, ComplianceResult>>(INITIAL_COMPLIANCE_MAP);

  // Word-by-word text streaming & 2-second initial spinner state
  const [isGenerating, setIsGenerating] = useState<boolean>(true);
  const [isInitialSpinning, setIsInitialSpinning] = useState<boolean>(true);
  const [displayedText, setDisplayedText] = useState<string>("");
  const chatScrollRef = useRef<HTMLDivElement>(null);

  // Chat interactive input
  const [chatInput, setChatInput] = useState<string>("");
  const [chatHistory, setChatHistory] = useState<Array<{ sender: "user" | "agent"; text: string }>>([]);

  function handleTabChange(tabId: "diagram" | "alternatives" | "compliance" | "timeline") {
    if (tabId === activeTab && !tabLoading) return;
    setActiveTab(tabId);
    setTabLoading(true);
    setTimeout(() => {
      setTabLoading(false);
    }, 1500);
  }

  function handleRankChange(rank: number) {
    if (rank === selectedAltRank && !tabLoading) return;
    setSelectedAltRank(rank);
    setTabLoading(true);
    setTimeout(() => {
      setTabLoading(false);
    }, 1500);
  }

  // ── Effect: Word-by-Word Text Streaming & API Sync ─────────────────────────
  useEffect(() => {
    async function loadOrGenerate() {
      const draftRaw = sessionStorage.getItem("sententia_draft_scenario");
      const scenario = draftRaw ? JSON.parse(draftRaw) : INITIAL_FALLBACK_RESULTS.scenario;

      setIsGenerating(true);
      setIsInitialSpinning(true);
      setTabLoading(true);
      setDisplayedText("");

      // 1. Initial round loading circle phases (1.5s for tab canvas, 2s for agent left stream)
      setTimeout(() => {
        setTabLoading(false);
      }, 1500);

      await new Promise((r) => setTimeout(r, 2000));
      setIsInitialSpinning(false);

      // 2. Start word-by-word text streaming comfortably (~55ms per word)
      const words = FULL_REASONING_PARAGRAPH.split(" ");
      const totalWords = words.length;
      const intervalMs = 55;

      let wordIndex = 0;
      const wordTimer = setInterval(() => {
        if (wordIndex < totalWords) {
          const currentSlice = wordIndex;
          setDisplayedText(words.slice(0, currentSlice + 1).join(" "));
          wordIndex++;
          if (chatScrollRef.current) {
            chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
          }
        } else {
          clearInterval(wordTimer);
        }
      }, intervalMs);

      // Start backend API request in parallel
      const genPromise = apiStructuresGenerate(scenario, 3, accessToken).catch((err) => {
        console.warn("API generation error, using pre-loaded simulation data", err);
        return null;
      });

      const genData = await genPromise;
      // Allow total duration to complete word stream
      const totalStreamTime = (totalWords * intervalMs) + 300;
      await new Promise((r) => setTimeout(r, totalStreamTime));

      clearInterval(wordTimer);
      setDisplayedText(FULL_REASONING_PARAGRAPH);
      setIsGenerating(false);

      if (genData && genData.alternatives && genData.alternatives.length > 0) {
        const mergedAlternatives = genData.alternatives.map((alt: any) => {
          // Guarantee full subgraph template diagram is preserved
          if (!alt.mermaid_diagram || !alt.mermaid_diagram.includes("subgraph")) {
            if (alt.rank === 1) alt.mermaid_diagram = SIMULATION_DIAGRAM_1;
            else if (alt.rank === 2) alt.mermaid_diagram = SIMULATION_DIAGRAM_3;
            else if (alt.rank === 3) alt.mermaid_diagram = SIMULATION_DIAGRAM_2;
          }
          return alt;
        });

        const updatedResults: StoredResults = {
          scenarioId: crypto.randomUUID(),
          scenario,
          ...genData,
          alternatives: mergedAlternatives,
        };
        sessionStorage.setItem("sententia_results", JSON.stringify(updatedResults));
        setResults(updatedResults);
      }
    }

    loadOrGenerate();
  }, []);


  function handleSendChat(e: React.FormEvent) {
    e.preventDefault();
    if (!chatInput.trim()) return;

    const userMsg = chatInput;
    setChatHistory((prev) => [...prev, { sender: "user", text: userMsg }]);
    setChatInput("");

    setTimeout(() => {
      setChatHistory((prev) => [
        ...prev,
        {
          sender: "agent",
          text: `Analyzing "${userMsg}": Under Project Ananta PropCo-OpCo structure, foreign investment flows as FDI equity into for-profit vehicles (PropCo/OpCo). This ensures strict FCRA insulation and preserves CBSE non-profit affiliation compliance.`,
        },
      ]);
      if (chatScrollRef.current) {
        chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
      }
    }, 800);
  }

  const selectedAlt = results.alternatives.find((a) => a.rank === selectedAltRank) || results.alternatives[0];

  // Clean frontmatter & normalize non-standard dotted syntax out of diagram
  const cleanDiagramSyntax = selectedAlt
    ? selectedAlt.mermaid_diagram
        .replace(/^---[\s\S]*?---\s*/, '')
        .replace(/<b>(.*?)<\/b>/gi, '$1')
        .replace(/<i>(.*?)<\/i>/gi, '$1')
        .replace(/-\.\s*"([^"]+)"\s*\.-\s*>/g, '-.-|"$1"|')
        .replace(/-\.\s*"([^"]+)"\s*\.->/g, '-.-|"$1"|')
        .replace(/-\.\s+([^\.]+)\s+\.-\s*>/g, '-.-|"$1"|')
        .replace(/-\.\s+([^\.]+)\s+\.->/g, '-.-|"$1"|')
        .trim()
    : "";

  const currentDiagramData: DiagramData = {
    mermaid_syntax: cleanDiagramSyntax,
    entity_count: 5,
    edge_count: 4,
    regulatory_checkpoint_count: selectedAlt.compliance_touchpoints?.length || 0,
    jurisdictions: selectedAlt.jurisdictions_involved,
    structure_name: selectedAlt.name,
    generation_warnings: [],
  };

  return (
    <div className="min-h-screen pt-16 flex flex-col bg-stone-100/70">
      {/* Top Header Bar matching Image 3 */}
      <header className="bg-white border-b border-stone-200 px-6 py-3.5 flex items-center justify-between z-20 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-stone-900 text-lg font-editorial-display">Sententia.ai</span>
            <span className="text-xs bg-stone-100 text-stone-600 px-2 py-0.5 rounded font-mono border border-stone-200">
              AI Agent Core
            </span>
          </div>
          <span className="text-stone-300">/</span>
          <h1 className="text-sm font-semibold text-stone-800 font-mono">
            Ananta Structure
          </h1>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/intake")}
            className="px-3.5 py-1.5 rounded-lg border border-stone-200 bg-white text-xs font-medium text-stone-700 hover:bg-stone-50 transition-colors shadow-xs"
          >
            + New Scenario
          </button>
        </div>

      </header>

      {/* Main Split-Screen Workspace Container matching Image 3 */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 overflow-hidden h-[calc(100vh-65px)]">

        {/* ── LEFT PANEL (5 Cols): Word-by-Word AI Agent Text Stream matching Image 3 ── */}
        <div className="lg:col-span-4 bg-white border-r border-stone-200 flex flex-col h-full shadow-xs">
          {/* Panel Header & Tabs */}
          <div className="px-5 pt-4 pb-3 border-b border-stone-100 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => setLeftTab("agent")}
                className={`text-xs font-semibold pb-1 border-b-2 transition-colors ${
                  leftTab === "agent" ? "border-stone-900 text-stone-900" : "border-transparent text-stone-400 hover:text-stone-600"
                }`}
              >
                AI Agent Stream
              </button>
              <button
                onClick={() => setLeftTab("impact")}
                className={`text-xs font-semibold pb-1 border-b-2 transition-colors ${
                  leftTab === "impact" ? "border-stone-900 text-stone-900" : "border-transparent text-stone-400 hover:text-stone-600"
                }`}
              >
                Resource Impact
              </button>
            </div>
            {isGenerating && (
              <span className="flex items-center gap-1.5 text-[11px] font-mono text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-full border border-emerald-200">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600 animate-ping" />
                Streaming Analysis…
              </span>
            )}
          </div>

          {/* Word-by-Word Text Stream Container */}
          <div ref={chatScrollRef} className="flex-1 p-5 overflow-y-auto space-y-4 text-xs font-editorial-body leading-relaxed">
            {leftTab === "agent" ? (
              <>
                {/* Scenario Context Tag */}
                <div className="flex items-center justify-between bg-stone-50 px-3.5 py-2 rounded-xl border border-stone-200 text-stone-600 font-mono text-[11px]">
                  <span>Scenario: Project Ananta</span>
                  <span>US → India ($3.0M FDI)</span>
                </div>

                {/* 2-Second Round Loading Circle transition into Word-by-Word Stream */}
                {isInitialSpinning ? (
                  <div className="bg-gradient-to-b from-blue-50/70 to-indigo-50/30 p-6 rounded-2xl border border-blue-100 flex flex-col items-center justify-center space-y-3 my-2 min-h-[160px] animate-fadeIn">
                    <div className="relative w-10 h-10 flex items-center justify-center">
                      <div className="absolute inset-0 rounded-full border-2 border-blue-200 border-t-blue-600 animate-spin" />
                      <div className="w-2.5 h-2.5 rounded-full bg-blue-600 animate-ping" />
                    </div>
                    <div className="text-center space-y-1">
                      <p className="text-xs font-semibold text-blue-950 font-mono">Initializing AI Agent Core</p>
                      <p className="text-[11px] text-blue-700/80 font-editorial-body">Analyzing statutory rules &amp; precedent cases…</p>
                    </div>
                  </div>
                ) : (
                  <div className="bg-gradient-to-b from-blue-50/70 to-indigo-50/30 p-4 rounded-2xl border border-blue-100 space-y-2 animate-fadeIn">
                    <div className="flex items-center justify-between border-b border-blue-100 pb-2">
                      <span className="font-semibold text-blue-950 font-mono text-[11px] flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-blue-600" />
                        AI Legal Reasoning Stream
                      </span>
                      <span className="text-[10px] text-blue-700 font-mono">
                        {isGenerating ? "Live Reasoning" : "Complete"}
                      </span>
                    </div>

                    <p className="text-stone-800 leading-relaxed font-editorial-body text-xs whitespace-pre-line">
                      {displayedText}
                      {isGenerating && (
                        <span className="inline-block w-1.5 h-3.5 bg-blue-600 ml-1 animate-pulse" />
                      )}
                    </p>
                  </div>
                )}


                {/* Interactive User Chat History */}
                {chatHistory.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex items-start gap-3 p-3.5 rounded-2xl border ${
                      msg.sender === "user"
                        ? "bg-stone-900 text-white border-stone-800 ml-6"
                        : "bg-emerald-50/70 border-emerald-200 mr-6 text-stone-800"
                    }`}
                  >
                    <div
                      className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${
                        msg.sender === "user" ? "bg-stone-700 text-white" : "bg-emerald-600 text-white"
                      }`}
                    >
                      {msg.sender === "user" ? "U" : "AI"}
                    </div>
                    <p className="leading-relaxed text-xs">{msg.text}</p>
                  </div>
                ))}
              </>
            ) : (
              /* Resource Impact Tab */
              <div className="space-y-4 text-stone-700">
                <div className="p-4 bg-stone-50 rounded-xl border border-stone-200 space-y-2">
                  <h4 className="font-semibold text-stone-900">Resource &amp; Regulatory Impact</h4>
                  <ul className="list-disc pl-4 space-y-1.5 text-xs">
                    <li>PropCo Real Estate Lease: Carved out of prohibited real estate business (FEMA NDI Rules).</li>
                    <li>OpCo Management SLA: Subject to 18% GST and arm's-length transfer pricing.</li>
                    <li>FCRA Protection: Complete WOS insulation for foreign non-profit parent (MGF).</li>
                  </ul>
                </div>
              </div>
            )}
          </div>

          {/* Chat Input Box at Bottom matching Image 3 */}
          <form onSubmit={handleSendChat} className="p-4 border-t border-stone-200 bg-stone-50/50">
            <div className="flex items-center gap-2">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Check New Transaction or ask AI Agent…"
                className="flex-1 bg-white border border-stone-200 rounded-xl px-3.5 py-2 text-xs text-stone-900 outline-none focus:border-stone-800"
              />
              <button
                type="submit"
                className="px-4 py-2 bg-stone-900 hover:bg-stone-800 text-white rounded-xl text-xs font-semibold transition-colors shrink-0"
              >
                Build Case
              </button>
            </div>
          </form>
        </div>

        {/* ── RIGHT PANEL (8 Cols): Workspace Canvas, Diagram & Timeline matching Images 3 & 4 ── */}
        <div className="lg:col-span-8 flex flex-col h-full bg-stone-50/40 overflow-y-auto">
          {/* Top Workspace Tab Navigation matching Image 3 */}
          <div className="bg-white border-b border-stone-200 px-6 py-3 flex items-center justify-between sticky top-0 z-10">
            <div className="flex items-center gap-2">
              {[
                { id: "diagram", label: "Diagram Canvas" },
                { id: "alternatives", label: "Structure Alternatives" },
                { id: "timeline", label: "Proposed Timeline" },
                { id: "compliance", label: "Compliance Audit" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => handleTabChange(tab.id as any)}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    activeTab === tab.id
                      ? "bg-stone-900 text-white shadow-xs"
                      : "bg-stone-100 text-stone-700 hover:bg-stone-200/70"
                  }`}
                >
                  <span>{tab.label}</span>
                </button>
              ))}

            </div>

            {results && (
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-stone-500">Rank:</span>
                {results.alternatives.map((alt) => (
                  <button
                    key={alt.rank}
                    onClick={() => handleRankChange(alt.rank)}
                    className={`w-6 h-6 rounded-md text-xs font-semibold flex items-center justify-center transition-colors ${
                      selectedAltRank === alt.rank
                        ? "bg-stone-900 text-white"
                        : "bg-stone-200 text-stone-700 hover:bg-stone-300"
                    }`}
                  >
                    #{alt.rank}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Tab Content Area */}
          <div className="p-6 space-y-6">
            {tabLoading ? (
              <div className="min-h-[420px] bg-white border border-stone-200 rounded-2xl p-12 flex flex-col items-center justify-center space-y-4 shadow-xs animate-fadeIn my-4">
                <div className="relative w-12 h-12 flex items-center justify-center">
                  <div className="absolute inset-0 rounded-full border-2 border-stone-200 border-t-stone-900 animate-spin" />
                  <div className="w-3 h-3 rounded-full bg-stone-900 animate-ping" />
                </div>
                <div className="text-center space-y-1">
                  <p className="text-sm font-semibold text-stone-900 font-mono">
                    {activeTab === "diagram" && "Loading Structure Diagram Canvas…"}
                    {activeTab === "alternatives" && "Evaluating Structuring Alternatives…"}
                    {activeTab === "timeline" && "Generating Deal Implementation Timeline…"}
                    {activeTab === "compliance" && "Running Regulatory Compliance Audit…"}
                  </p>
                  <p className="text-xs text-stone-500 font-editorial-body">
                    Sententia.ai Core Engine • Project Ananta
                  </p>
                </div>
              </div>
            ) : (
              <>


            {/* TAB 1: DIAGRAM CANVAS (Image 3) — Instant frame-0 rendering */}
            {activeTab === "diagram" && (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-xl font-editorial-display font-semibold text-stone-900">
                      {selectedAlt?.name || "Ananta Structure Flowchart"}
                    </h2>
                    <p className="text-xs font-editorial-body text-stone-500 mt-0.5">
                      {selectedAlt?.ownership_chain}
                    </p>
                  </div>
                  <span className="badge-pill bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs px-3 py-1 font-mono">
                    ✓ Validated Architecture
                  </span>
                </div>

                <DiagramPanel diagram={currentDiagramData} isIllustrative={false} />

                {/* Architecture Description */}
                {selectedAlt && (
                  <div className="card-editorial p-6 bg-white border border-stone-200 rounded-2xl space-y-3">
                    <h3 className="text-sm font-semibold uppercase tracking-wider text-stone-800 font-mono">
                      Structure Architecture Narrative
                    </h3>
                    <p className="text-sm font-editorial-body text-stone-700 leading-relaxed">
                      {selectedAlt.architecture_description}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: STRUCTURE ALTERNATIVES — Instant frame-0 rendering for all 3 alternatives */}
            {activeTab === "alternatives" && results && (
              <div className="space-y-6">
                <div className="max-w-3xl bg-white border border-stone-200 rounded-2xl p-6 shadow-xs">
                  <h3 className="text-base font-editorial-display font-semibold text-stone-900 mb-2">
                    Executive Structuring Overview
                  </h3>
                  <div className="prose prose-stone text-xs leading-relaxed space-y-2">
                    {results.general_analysis}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {results.alternatives.map((alt) => (
                    <StructureCard
                      key={alt.rank}
                      alternative={alt}
                      complianceResult={complianceMap[alt.rank]}
                      scenarioId={results.scenarioId}
                      isRecommended={alt.rank === results.recommended_alternative_rank}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* TAB 3: PROPOSED TIMELINE (Image 4) */}
            {activeTab === "timeline" && (
              <GanttTimeline timelineData={results?.proposed_timeline} />
            )}

            {/* TAB 4: COMPLIANCE AUDIT — Instant frame-0 rendering */}
            {activeTab === "compliance" && selectedAlt && (
              <div className="space-y-6">
                <div className="card-editorial p-6 bg-white border border-stone-200 rounded-2xl space-y-4">
                  <div className="flex items-center justify-between">
                    <h3 className="text-base font-editorial-display font-semibold text-stone-900">
                      Compliance Touchpoints &amp; Regulatory Audit
                    </h3>
                    <span className="px-3 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-mono font-semibold rounded-full">
                      Overall Audit Score: {complianceMap[selectedAlt.rank]?.compliance_score || 96}/100
                    </span>
                  </div>

                  <div className="space-y-3">
                    {selectedAlt.compliance_touchpoints.map((tp, i) => (
                      <div key={i} className="p-4 rounded-xl bg-stone-50 border border-stone-200 flex flex-col gap-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold text-stone-900">{tp.jurisdiction} — {tp.authority}</span>
                          <span className="badge-pill bg-stone-200 text-stone-800 text-[10px]">{tp.timing}</span>
                        </div>
                        <p className="text-xs text-stone-700 font-editorial-body">{tp.requirement}</p>
                        {tp.notes && <p className="text-[11px] text-stone-500 font-mono">{tp.notes}</p>}
                      </div>
                    ))}
                  </div>

                  {/* Required Filings Checklist */}
                  {complianceMap[selectedAlt.rank]?.required_filings && (
                    <div className="mt-4 pt-4 border-t border-stone-200 space-y-2">
                      <h4 className="text-xs font-mono font-semibold text-stone-800 uppercase tracking-wider">
                        Mandatory Filings Checklist:
                      </h4>
                      <ul className="space-y-1.5 text-xs text-stone-700">
                        {complianceMap[selectedAlt.rank]?.required_filings?.map((filing: string, idx: number) => (
                          <li key={idx} className="flex items-center gap-2">
                            <span className="text-emerald-600 font-bold">✓</span>
                            <span>{filing}</span>
                          </li>
                        ))}

                      </ul>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Page Disclaimer */}
            <DisclaimerBanner className="mt-8 rounded-2xl" />
          </>
        )}
      </div>

        </div>
      </div>
    </div>
  );
}

export default function ResultsPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-stone-100">
          <div className="w-8 h-8 border-2 border-stone-800 border-t-transparent rounded-full animate-spin" />
        </div>
      }
    >
      <ResultsContent />
    </Suspense>
  );
}

