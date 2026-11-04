import { useState, useEffect, useCallback } from "react";
import {
  Download,
  Bot,
  Activity,
  BarChart3,
  ExternalLink,
  X,
  RefreshCw,
  FolderKanban,
  LayoutDashboard,
  List,
  Settings,
  FileText,
} from "lucide-react";
import type {
  PipelineRow,
  Cluster,
  OpportunityData,
  SyncBanner,
  View,
  SourceFilter,
  StatusFilter,
  GoldenRow,
  EvidenceQuestion,
  EvidenceCategory,
  EvidenceTestResult,
  EvidenceCategorySummary,
  EvidenceLogData,
  GoldenTestResponse,
} from "./types";

const API_BASE = "/api";

const SOURCES: SourceFilter[] = [
  "All Sources",
  "Reddit",
  "Google Play",
  "App Store",
  "YouTube",
  "TradingQ&A",
  "X",
  "ChatGPT",
  "Gemini",
];

const TRIGGER_COLORS: Record<string, string> = {
  "Anxiety on negative portfolio returns": "#a78bfa",
  "Cash-flow crunch / salary date mismatch": "#a78bfa",
  "Information overload / confusion about CAGR vs absolute returns": "#a78bfa",
  "App friction / autodebit (NACH/UPI mandate) failures": "#a78bfa",
};

function shortDate(iso: string | undefined | null): string {
  if (!iso) return "-";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso.slice(0, 10);
  }
}

function scoreColor(score: number | null): string {
  if (score == null) return "text-slate-500";
  if (score >= 75) return "text-violet-400 font-bold";
  if (score >= 60) return "text-slate-300 font-bold";
  return "text-slate-500";
}

function sentimentColor(label: string | null): string {
  if (!label) return "text-slate-500";
  switch (label) {
    case "Positive":
      return "text-emerald-400";
    case "Critical":
      return "text-rose-400 font-bold";
    case "Negative":
      return "text-amber-400";
    default:
      return "text-slate-600";
  }
}

function sourceDotColor(source: string): string {
  switch (source) {
    case "Reddit": return "#fb923c";
    case "Google Play": return "#34d399";
    case "App Store": return "#60a5fa";
    case "YouTube": return "#f87171";
    case "TradingQ&A": return "#c4b5fd";
    default: return "#64748b";
  }
}

function linkStatusColor(status: string | null | undefined): string {
  switch (status) {
    case "working": return "#34d399";
    case "broken": return "#f87171";
    case "timeout": return "#fbbf24";
    case "unchecked": return "#94a3b8";
    default: return "#64748b";
  }
}

export default function App() {
  const [view, setView] = useState<View>("sheet");
  const [rows, setRows] = useState<PipelineRow[]>([]);
  const [counts, setCounts] = useState({ total: 0, clean_count: 0, noise_count: 0 });
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("clean");
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("All Sources");
  const [search, setSearch] = useState("");
  const [banner, setBanner] = useState<SyncBanner | null>(null);
  const [bannerDismissed, setBannerDismissed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [opp, setOpp] = useState<OpportunityData | null>(null);
  const [selectedCluster, setSelectedCluster] = useState<Cluster | null>(null);
  const [evidence, setEvidence] = useState<EvidenceLogData | null>(null);
  const [goldenTest, setGoldenTest] = useState<GoldenTestResponse | null>(null);
  const [goldenTestLoading, setGoldenTestLoading] = useState(false);

  const fetchRows = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter === "clean") params.set("status", "CLEAN_SIP_SIGNAL");
      else if (statusFilter === "noise") params.set("status", "FILTERED_NON_SIP,FILTERED_SPAM_PROMO");
      if (sourceFilter && sourceFilter !== "All Sources") params.set("source", sourceFilter);
      if (search) params.set("search", search);
      params.set("limit", "200");
      params.set("offset", "0");
      const res = await fetch(`${API_BASE}/rows?${params}`);
      const data = await res.json();
      setRows(data.rows || []);
      setCounts({
        total: data.total ?? 0,
        clean_count: data.clean_count ?? 0,
        noise_count: data.noise_count ?? 0,
      });
    } finally {
      setLoading(false);
    }
  }, [statusFilter, sourceFilter, search]);

  const fetchOpp = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/opportunity`);
      const data = await res.json();
      setOpp(data);
    } catch {
      /* offline OK */
    }
  }, []);

  const fetchEvidence = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/evidence-log`);
      const data = await res.json();
      setEvidence(data);
    } catch {
      /* offline OK */
    }
  }, []);

  const runGoldenTest = useCallback(async () => {
    setGoldenTestLoading(true);
    try {
      const res = await fetch(`${API_BASE}/evidence-log/run-golden-test`, { method: "POST" });
      const data = await res.json();
      setGoldenTest(data);
    } catch (err) {
      setGoldenTest({ status: "error", total_rows: 0, pass_count: 0, fail_count: 0, pass_rate: 0, threshold: 0.8, overall_pass: false, results: [], category_summary: [] } as GoldenTestResponse);
    } finally {
      setGoldenTestLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRows();
  }, [fetchRows]);

  useEffect(() => {
    if (view === "dashboard") fetchOpp();
    if (view === "evidence") fetchEvidence();
  }, [view, fetchOpp, fetchEvidence]);

  const showBanner = banner && !bannerDismissed;

  const handleIngest = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/ingest`, { method: "POST" });
      const data = await res.json();
      setBanner({
        rows_scanned: data.inserted_new,
        rows_inserted: data.inserted_new,
        provider: "scrapers",
        supabase: data.supabase_sync?.status || "ok",
        message: `Pulled scrapers — ${data.inserted_new} new rows inserted (clean: ${data.clean_count}, noise: ${data.noise_count})${data.refinement ? ` · refined: ${data.refinement.out}/${data.refinement.in} (${data.refinement.dropped_dup} dups, ${data.refinement.dropped_language} lang)` : ""}`,
      });
      setBannerDismissed(false);
      await fetchRows();
    } catch (err) {
      setBanner({ message: `Ingest failed: ${(err as Error).message}` });
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/pipeline/analyze`, { method: "POST" });
      const data = await res.json();
      setBanner({
        rows_inserted: data.rows_tagged,
        provider: data.provider || "deterministic",
        supabase: data.supabase_sync?.status || "ok",
        message: `AI analysis complete — ${data.rows_tagged} rows tagged via ${data.provider || "deterministic"}`,
      });
      setBannerDismissed(false);
      setView("dashboard");
      await fetchRows();
      await fetchOpp();
    } catch (err) {
      setBanner({ message: `Analysis failed: ${(err as Error).message}` });
    } finally {
      setLoading(false);
    }
  };

  const dismissBanner = () => setBannerDismissed(true);

  const handleValidateLinks = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/validate-links`, { method: "POST" });
      const data = await res.json();
      setBanner({
        rows_scanned: data.checked,
        rows_inserted: data.checked,
        provider: "link-validator",
        supabase: "ok",
        message: `Link check complete — ${data.checked} URLs checked (${data.by_status?.working ?? 0} working, ${data.by_status?.broken ?? 0} broken, ${data.by_status?.timeout ?? 0} timeout)`,
      });
      setBannerDismissed(false);
      await fetchRows();
    } catch (err) {
      setBanner({ message: `Link validation failed: ${(err as Error).message}` });
    } finally {
      setLoading(false);
    }
  };

  const filteredRows = rows.filter((r) => {
    if (search) {
      const q = search.toLowerCase();
      if (!r.content.toLowerCase().includes(q) && !r.title?.toLowerCase().includes(q))
        return false;
    }
    return true;
  });

  const cleanLabel = statusFilter === "clean" ? "Cleaned SIP Rows" : "Filtered Noise";
  const cleanCount = statusFilter === "clean" ? counts.clean_count : counts.noise_count;

  const topCluster = opp?.top_cluster ?? selectedCluster ?? null;
  const clusters = opp?.clusters ?? [];

  return (
    <div className="app-shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="w-8 h-8 rounded-lg bg-violet-600 flex items-center justify-center text-white font-bold">
            G
          </div>
          <div>
            <div className="sidebar-brand">Groww Discovery</div>
            <div className="sidebar-brand-sub">Behavioral Engine</div>
          </div>
        </div>
        <nav className="sidebar-nav">
          <button
            className={`nav-item ${view === "sheet" ? "active" : "default"}`}
            onClick={() => setView("sheet")}
          >
            <List className="nav-item-icon" />
            <span>Data Sheet</span>
          </button>
          <button
            className={`nav-item ${view === "dashboard" ? "active" : "default"}`}
            onClick={() => setView("dashboard")}
          >
            <LayoutDashboard className="nav-item-icon" />
            <span>Opportunity Dashboard</span>
          </button>
          <button
            className={`nav-item ${view === "evidence" ? "active" : "default"}`}
            onClick={() => setView("evidence")}
          >
            <FileText className="nav-item-icon" />
            <span>AI Evidence Log</span>
          </button>
          <div className="px-4 py-2 text-[10px] uppercase tracking-widest text-slate-500 font-mono-nums mb-3">
            Actions
          </div>
          <button
            className="nav-item btn-ghost"
            onClick={handleIngest}
            disabled={loading}
          >
            <Download className="nav-item-icon" />
            <span>Pull Scrapers</span>
          </button>
          <button
            className={`nav-item btn-primary ${loading ? "opacity-50 cursor-not-allowed" : ""}`}
            onClick={handleAnalyze}
            disabled={loading}
          >
            <Bot className="nav-item-icon" />
            <span>AI Analysis</span>
          </button>
          <button
            className={`nav-item btn-ghost ${loading ? "opacity-50 cursor-not-allowed" : ""}`}
            onClick={handleValidateLinks}
            disabled={loading}
          >
            <RefreshCw className="nav-item-icon" />
            <span>Validate Links</span>
          </button>
        </nav>
        <div className="sidebar-footer">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-xs font-bold text-slate-300">
              AG
            </div>
            <div>
              <div className="text-sm font-semibold text-slate-100">Admin</div>
              <div className="text-xs text-slate-500 font-mono-nums">groww-discovery.local</div>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-slate-800">
            <button className="nav-item btn-ghost text-xs">
              <Settings className="nav-item-icon" />
              <span>Settings</span>
            </button>
          </div>
        </div>
      </aside>

      {/* Main */}
      <main className="main">
        <header className="header">
          <div className="flex flex-col gap-1">
            <div className="flex items-center gap-3">
              <h1 className="header-title">
                {view === "sheet" ? "Data Sheet" : "Opportunity Dashboard"}
              </h1>
              <span className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse"></span>
            </div>
            <p className="header-sub">
              {view === "sheet"
                ? `SIP investor feedback · ${counts.clean_count} clean · ${counts.noise_count} noise`
                : "Behavioral trigger clusters · opportunity scoring"}
            </p>
          </div>
          <div className="mt-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <input
                className="w-64 px-3 py-2 text-sm border border-slate-700 rounded-lg bg-slate-900 text-slate-100 focus:ring-2 focus:ring-violet-500/30 focus:outline-none"
                placeholder="Search investor text…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500 font-mono-nums">
                {loading ? "syncing…" : "idle"}
              </span>
            </div>
          </div>
        </header>

        {/* Live Sync Banner */}
        {showBanner && (
          <div className="banner mt-4">
            <div className="flex items-center gap-2">
              <Activity className="w-4 h-4 animate-spin text-violet-400" />
              <span>{banner.message}</span>
            </div>
            <button className="text-slate-500 hover:text-slate-200" onClick={dismissBanner}>
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        <div className="content">
          {view === "sheet" ? (
            <ViewSheet
              rows={filteredRows}
              counts={counts}
              cleanLabel={cleanLabel}
              cleanCount={cleanCount}
              statusFilter={statusFilter}
              setStatusFilter={setStatusFilter}
              sourceFilter={sourceFilter}
              setSourceFilter={setSourceFilter}
              search={search}
              setSearch={setSearch}
              loading={loading}
            />
          ) : view === "dashboard" ? (
          <ViewDashboard
            clusters={clusters}
            topCluster={topCluster}
            setSelectedCluster={setSelectedCluster}
            selectedCluster={selectedCluster}
            setView={setView}
            totalTagged={opp?.total_tagged_rows ?? 0}
          />
          ) : (
          <ViewEvidenceLog
            evidence={evidence}
            goldenTest={goldenTest}
            runGoldenTest={runGoldenTest}
            goldenTestLoading={goldenTestLoading}
          />
          )}
        </div>
      </main>
    </div>
  );
}

function ViewSheet({
  rows,
  counts,
  cleanLabel,
  cleanCount,
  statusFilter,
  setStatusFilter,
  sourceFilter,
  setSourceFilter,
  search,
  setSearch,
  loading,
}: {
  rows: PipelineRow[];
  counts: { total: number; clean_count: number; noise_count: number };
  cleanLabel: string;
  cleanCount: number;
  statusFilter: StatusFilter;
  setStatusFilter: (v: StatusFilter) => void;
  sourceFilter: SourceFilter;
  setSourceFilter: (v: SourceFilter) => void;
  search: string;
  setSearch: (v: string) => void;
  loading: boolean;
}) {
  return (
    <div className="space-y-5">
      {/* Filter Row */}
      <div className="card flex flex-col gap-4">
        <div className="flex items-center gap-3 text-sm font-medium text-slate-400">
          <span className="text-slate-100">{cleanLabel}</span>
          <span className="font-mono-nums text-violet-400 font-bold">({cleanCount})</span>
          <span className="text-slate-600">·</span>
          <span className="text-slate-500">Filtered Noise ({counts.noise_count})</span>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            className={`pill ${statusFilter === "clean" ? "active" : "default"}`}
            onClick={() => setStatusFilter("clean")}
          >
            Cleaned SIP Rows
          </button>
          <button
            className={`pill ${statusFilter === "noise" ? "active" : "default"}`}
            onClick={() => setStatusFilter("noise")}
          >
            Filtered Noise
          </button>
          {SOURCES.map((s) => (
            <button
              key={s}
              className={`pill ${sourceFilter === s ? "active" : "default"}`}
              onClick={() => setSourceFilter(s)}
            >
              {s}
            </button>
          ))}
          <div className="flex-1 min-w-[220px]">
            <input
              className="w-full px-3 py-2 text-sm border border-slate-700 rounded-lg bg-slate-900 text-slate-100 focus:ring-2 focus:ring-violet-500/30 focus:outline-none"
              placeholder="Search investor text…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* Spreadsheet Table */}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th className="w-[40px]">#</th>
              <th>Source</th>
              <th className="w-[80px]">Date</th>
              <th className="w-[50px]">Votes</th>
              <th>Cleaned Investor Feedback</th>
              <th className="w-[220px]">AI Behavioral Trigger</th>
              <th className="w-[110px]">Sentiment</th>
              <th className="w-[150px]">Segment Proxy</th>
              <th className="w-[120px]">Drop-Off</th>
              <th className="w-[80px]">Opp Score</th>
              <th className="w-[120px]">Source Link</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => {
              const isNoise = r.cleaning_status !== "CLEAN_SIP_SIGNAL";
              return (
                <tr key={r.content_hash || i}>
                  <td className="font-mono-nums text-slate-500">{i + 1}</td>
                  <td className="flex items-center gap-2">
                    <span
                      className="source-dot"
                      style={{ backgroundColor: sourceDotColor(r.source) }}
                    ></span>
                    <span className="text-slate-300">{r.source}</span>
                  </td>
                  <td className="font-mono-nums text-slate-500">{shortDate(r.date)}</td>
                  <td className="font-mono-nums text-slate-500">{r.votes ?? 0}</td>
                  <td className={isNoise ? "italic text-slate-500" : "text-slate-200"}>
                    {r.content}
                  </td>
                  <td>
                    {isNoise ? (
                      <span className="italic text-slate-500 text-sm">
                        {r.removal_reason || "Removed by Stage 2 noise filter"}
                      </span>
                    ) : (
                      <div>
                        <span className="text-xs font-medium text-slate-400 block mb-0.5">
                          {r.behavioral_trigger || "—"}
                        </span>
                      </div>
                    )}
                  </td>
                  <td>
                    <span className={`badge ${sentimentColor(r.sentiment_label ?? null)}`}>
                      {r.sentiment_label || "—"}
                    </span>
                  </td>
                  <td className="font-mono-nums text-slate-500">
                    {r.segment_proxy_ticket || "—"}
                  </td>
                  <td className="font-mono-nums text-slate-500">
                    {r.retention_dropoff_bucket ?? "—"}
                  </td>
                  <td className="font-mono-nums">
                    <span className={`badge badge-score ${scoreColor(r.opportunity_score ?? 0)}`}>
                      {r.opportunity_score ?? "—"}
                    </span>
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      {r.url ? (
                        <a
                          href={String(r.url)}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-violet-400 hover:underline font-mono-nums"
                        >
                          Open source <ExternalLink className="w-3 h-3 ml-0.5 inline" />
                        </a>
                      ) : (
                        <span className="text-xs text-slate-600">—</span>
                      )}
                      <span
                        className={`badge ${linkStatusColor(r.link_status ?? null)} text-[9px] px-2`}
                        style={{ borderColor: linkStatusColor(r.link_status ?? null) + "50" }}
                      >
                        {r.link_status === null || r.link_status === undefined ? "unchecked" : r.link_status}
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={11} className="text-center py-12 text-slate-500">
                  No rows found. Click "Pull Scrapers" in the sidebar to ingest data.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-xs text-slate-500 mt-3">
        <span>Showing {rows.length} of {counts.total} rows</span>
        <span className="font-mono-nums">{loading ? "loading…" : "idle"}</span>
      </div>
    </div>
  );
}

function ViewDashboard({
  clusters,
  topCluster,
  setSelectedCluster,
  selectedCluster,
  setView,
  totalTagged,
}: {
  clusters: Cluster[];
  topCluster: Cluster | null;
  setSelectedCluster: (c: Cluster | null) => void;
  selectedCluster: Cluster | null;
  setView: (v: View) => void;
  totalTagged: number;
}) {
  const selected = selectedCluster ?? topCluster ?? null;

  return (
    <div className="space-y-6">
      {/* KPI Cards - Top Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="kpi-card">
          <div className="flex items-center justify-between mb-3">
            <div>
              <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold">Opportunity Score</div>
              <div className="text-2xl font-bold text-slate-100 mt-1">
                {selected ? selected.opportunity_score : "—"} <span className="text-xs font-normal text-slate-500">/100</span>
              </div>
            </div>
            <div className="gauge-wrap">
              <svg className="w-full h-full" viewBox="0 0 40 40">
                <circle cx="20" cy="20" r="16" fill="none" stroke="#1e293b" strokeWidth="3" />
                <circle
                  cx="20" cy="20" r="16"
                  fill="none"
                  stroke="#8b5cf6"
                  strokeWidth="3"
                  strokeDasharray={selected ? (selected.opportunity_score / 100) * 100.53 : 0}
                  strokeDashoffset={selected ? 100.53 - (selected.opportunity_score / 100) * 100.53 : 100.53}
                  strokeLinecap="round"
                  transform="rotate(-90 20 20)"
                />
              </svg>
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                <span className="font-mono-nums font-bold text-slate-100">
                  {selected ? selected.opportunity_score : "—"}
                </span>
              </div>
            </div>
          </div>
          <div className="text-xs text-slate-500">{totalTagged} tagged SIP rows</div>
        </div>

        {[
          { label: "Months 1-3", key: "months_1_to_3_pct" },
          { label: "Months 6-8", key: "months_6_to_8_pct" },
          { label: "Months 10-12", key: "months_10_to_12_pct" },
        ].map((k, idx) => {
          const pct = Number(selected?.[k.key as keyof Cluster] ?? 0);
          const count = selected ? Math.round((pct / 100) * selected.row_count) : 0;
          return (
            <div key={idx} className="kpi-card">
              <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold">{k.label}</div>
              <div className="text-xl font-bold text-slate-100 mt-1">{pct}%</div>
              <div className="text-xs text-slate-500 mt-0.5">{count} investors</div>
              <div className="mt-2 h-1 bg-slate-800 rounded-full overflow-hidden">
                <div className={`h-full bg-violet-600`} style={{ width: `${pct}%` }}></div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Main Split Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Clusters Table (7 cols) */}
        <div className="lg:col-span-7 card">
          <div className="px-6 py-4 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-violet-400" />
              <span className="font-semibold text-slate-100">Behavioral Trigger Clusters</span>
            </div>
          </div>
          <div className="overflow-y-auto max-h-[60vh]">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 border-b border-slate-800 bg-slate-800/50">Behavioral Trigger</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 border-b border-slate-800 bg-slate-800/50 text-right w-[100px]">Share / Rows</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 border-b border-slate-800 bg-slate-800/50 text-right w-[110px]">Intensity / Polarity</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 border-b border-slate-800 bg-slate-800/50 w-[130px]">12M Drop-Off</th>
                  <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-slate-500 border-b border-slate-800 bg-slate-800/50 text-right w-[80px]">Score</th>
                </tr>
              </thead>
              <tbody>
                {clusters.map((c) => {
                  const isSelected = selected?.trigger === c.trigger;
                  return (
                    <tr
                      key={c.trigger}
                      onClick={() => setSelectedCluster(c)}
                      className={`cursor-pointer transition-colors hover:bg-slate-800/30 ${isSelected ? "bg-violet-500/10 border-l-2 border-l-violet-500" : ""}`}
                    >
                      <td className="px-4 py-4 border-b border-slate-800">
                        <div className="flex items-center gap-3">
                          <span className="source-dot" style={{ backgroundColor: TRIGGER_COLORS[c.trigger] }}></span>
                          <div>
                            <div className="font-semibold text-slate-100 text-sm">{c.display}</div>
                            <div className="text-xs text-slate-500 font-mono-nums">
                              {c.dominant_ticket} · {c.dominant_tenure}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-4 border-b border-slate-800 text-right font-mono-nums">
                        <div className="font-semibold text-slate-100">{c.share_pct}%</div>
                        <div className="text-xs text-slate-500">{c.row_count} rows</div>
                      </td>
                      <td className="px-4 py-4 border-b border-slate-800 text-right">
                        <div className="font-mono-nums text-slate-300">{c.avg_emotional_intensity}/10</div>
                        <div className="text-xs text-slate-500">pol {c.avg_sentiment_polarity}</div>
                      </td>
                      <td className="px-4 py-4 border-b border-slate-800">
                        <div className="flex gap-2">
                          {[
                            { label: "M1-3", pct: c.months_1_to_3_pct },
                            { label: "M6-8", pct: c.months_6_to_8_pct },
                            { label: "M10-12", pct: c.months_10_to_12_pct },
                          ].map((seg) => (
                            <div key={seg.label} className="flex-1 h-1.5 bg-slate-800 rounded-full">
                              <div className="h-full bg-violet-600 rounded-full" style={{ width: `${seg.pct}%` }}></div>
                            </div>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-4 border-b border-slate-800 text-right">
                        <span className={`badge badge-score ${scoreColor(c.opportunity_score)}`}>
                          {c.opportunity_score}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right: Selected Opportunity Inspector (5 cols) */}
        <div className="lg:col-span-5">
          {selected ? (
            <div className="space-y-4">
              <div className="card">
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <span className="badge bg-violet-500/10 text-violet-400 border-violet-500/20 font-mono-nums">
                      Score {selected.opportunity_score}/100
                    </span>
                  </div>
                  <button
                    className="btn btn-outline text-xs"
                    onClick={() => {
                      setSelectedCluster(null);
                      setView("sheet");
                    }}
                  >
                    View in Data Sheet <ExternalLink className="w-3 h-3 ml-1" />
                  </button>
                </div>
                <div className="text-lg font-bold text-slate-100 mb-1">{selected.display}</div>
                <div className="text-sm text-slate-400 mb-3">
                  {selected.row_count} investor narratives · {selected.share_pct}% of tagged SIP signal
                </div>
                <div className="intervention mb-3">
                  <div className="text-xs uppercase tracking-wider text-violet-400 font-semibold mb-1">Recommended Product Action</div>
                  <div className="text-sm text-slate-300">{selected.recommended_intervention}</div>
                </div>
                <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">Verbatim Investor Quotes</div>
                {selected.quotes.map((q, i) => (
                  <div key={i} className="quote">
                    <p>"{q.text}"</p>
                    <div className="quote-meta">{q.source} · {q.dropoff_window} drop-off window</div>
                  </div>
                ))}
              </div>
              <div className="card border border-slate-800 bg-slate-900/50 p-4 rounded-xl">
                <div className="text-xs uppercase tracking-wider text-slate-500 font-semibold mb-2">12-Month Retention Drop-Off</div>
                <div className="space-y-2">
                  {[
                    { label: "Months 1-3", pct: selected.months_1_to_3_pct },
                    { label: "Months 6-8", pct: selected.months_6_to_8_pct },
                    { label: "Months 10-12", pct: selected.months_10_to_12_pct },
                  ].map((seg) => (
                    <div key={seg.label} className="flex items-center justify-between text-sm">
                      <span className="text-slate-400">{seg.label}</span>
                      <span className="font-mono-nums font-bold text-slate-100">{seg.pct}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="card h-[400px] flex flex-col items-center justify-center text-center">
              <FolderKanban className="w-12 h-12 text-slate-600 mb-3" />
              <div className="text-slate-400 text-sm">Select a behavioral trigger cluster to inspect</div>
              <div className="text-xs text-slate-600 mt-1">Opportunity score · intervention · verbatim quotes</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function ViewEvidenceLog({
  evidence,
  goldenTest,
  runGoldenTest,
  goldenTestLoading,
}: {
  evidence: EvidenceLogData | null;
  goldenTest: GoldenTestResponse | null;
  runGoldenTest: () => void;
  goldenTestLoading: boolean;
}) {
  const categories = evidence?.categories ?? [];
  const questions = evidence?.questions ?? [];
  const goldenRows = evidence?.golden_rows ?? [];
  const results = goldenTest?.results ?? [];
  const categorySummary = goldenTest?.category_summary ?? [];

  const resultById = new Map(results.map((r) => [r.id, r]));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-2">
          <FileText className="w-6 h-6 text-violet-400" />
          <div>
            <h2 className="text-xl font-bold text-slate-100">AI Evidence Log</h2>
            <p className="text-sm text-slate-400">
              Demonstrate how the discovery engine gathers &amp; analyzes data, identifies themes,
              generates insights, and validates insight quality against a golden dataset.
            </p>
          </div>
        </div>
        {goldenTest && (
          <div className="mt-4 flex items-center gap-4 pt-4 border-t border-slate-800">
            <div className="flex-1 grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700">
                <div className="text-xs text-slate-400 uppercase tracking-wider">Golden rows tested</div>
                <div className="text-xl font-bold text-slate-100">{goldenTest.total_rows}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700">
                <div className="text-xs text-slate-400 uppercase tracking-wider">Passed</div>
                <div className="text-xl font-bold text-emerald-400">{goldenTest.pass_count}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700">
                <div className="text-xs text-slate-400 uppercase tracking-wider">Failed</div>
                <div className="text-xl font-bold text-rose-400">{goldenTest.fail_count}</div>
              </div>
              <div className="p-3 rounded-xl bg-slate-800/50 border border-slate-700">
                <div className="text-xs text-slate-400 uppercase tracking-wider">Pass rate</div>
                <div className="text-xl font-bold">
                  <span className={goldenTest.overall_pass ? "text-emerald-400" : "text-rose-400"}>
                    {(goldenTest.pass_rate * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={runGoldenTest}
              disabled={goldenTestLoading}
              className="px-4 py-2 rounded-lg border border-violet-500/30 bg-violet-500/10 text-violet-400 text-sm font-medium hover:bg-violet-500/20 disabled:opacity-50 flex items-center gap-2"
            >
              {goldenTestLoading ? (
                <Activity className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              <span>Run Golden Dataset Test</span>
            </button>
          </div>
        )}
      </div>

      {/* Four pipeline stages */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {categories.map((cat) => {
          const summary = categorySummary.find((s) => s.category_id === cat.id);
          const passRate = summary ? summary.pass_rate : 0;
          const catRows = goldenRows.filter((r) => r.evidence_category === cat.id);
          return (
            <div key={cat.id} className="card p-5">
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 rounded-lg bg-violet-500/20 flex items-center justify-center text-violet-400 font-bold text-xs">
                  {cat.id.charAt(0).toUpperCase()}
                </div>
                <div>
                  <div className="font-semibold text-slate-100">{cat.name}</div>
                  <div className="text-xs text-slate-400">{cat.description}</div>
                </div>
              </div>
              {summary && (
                <div className="mb-3">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Golden test pass rate</span>
                    <span className="font-mono-nums font-bold">
                      {passRate === 0 ? "—" : (passRate * 100).toFixed(0)}%
                    </span>
                  </div>
                  <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className={`h-full ${passRate >= 0.8 ? "bg-emerald-500" : "bg-rose-500"}`} style={{ width: `${Math.round(passRate * 100)}%` }}></div>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    {summary.pass} passed · {summary.fail} failed · {summary.total} total
                  </div>
                </div>
              )}
              <div className="text-xs text-slate-500 mb-3">
                {catRows.length} golden row(s) in this category
              </div>
            </div>
          );
        })}
      </div>

      {/* Mentor-testable questions */}
      <div className="card p-5">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold text-xs">
            Q
          </div>
          <div>
            <div className="font-semibold text-slate-100">Mentor-Testable AI Evidence Questions</div>
            <div className="text-xs text-slate-400">Questions mentors can use to verify the discovery engine is working</div>
          </div>
        </div>
        <div className="space-y-3">
          {questions.map((q) => (
            <div key={q.id} className="p-4 rounded-xl border border-slate-800 bg-slate-900/50">
              <div className="flex justify-between items-start mb-2">
                <span className="px-2 py-0.5 rounded bg-slate-800 text-xs font-bold text-violet-400">
                  {q.id}
                </span>
                <span className="text-xs text-slate-500 font-mono-nums">{q.category}</span>
              </div>
              <div className="font-medium text-slate-200 mb-2">{q.question}</div>
              <div className="text-xs text-slate-400 mb-2">
                <span className="font-semibold text-slate-500">Expected:</span> {q.expected}
              </div>
              <div className="text-xs text-slate-500 mb-2">
                <span className="font-semibold text-slate-500">Test:</span> {q.test}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Golden dataset rows with test results */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-slate-700 flex items-center justify-center text-slate-400 font-bold text-xs">
              GD
            </div>
            <div>
              <div className="font-semibold text-slate-100">Golden Dataset Rows</div>
              <div className="text-xs text-slate-400">Pre-labeled SIP investor posts with expected tags</div>
            </div>
          </div>
          <span className="text-xs text-slate-500 font-mono-nums">{goldenRows.length} rows</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm border-collapse">
            <thead>
              <tr className="text-slate-500 uppercase text-[10px] tracking-wider">
                <th className="pb-3">ID</th>
                <th className="pb-3">Source</th>
                <th className="pb-3">Content</th>
                <th className="pb-3 text-right">Expected Trigger</th>
                <th className="pb-3 text-right">Actual Trigger</th>
                <th className="pb-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody>
              {goldenRows.map((row) => {
                const result = resultById.get(row.id);
                const isNoise = row.is_noise;
                return (
                  <tr key={row.id} className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors">
                    <td className="py-3 font-mono-nums text-slate-400 text-xs">{row.id}</td>
                    <td className="py-3 text-slate-300">
                      <span className="source-dot" style={{ backgroundColor: sourceDotColor(row.source) }}></span>{" "}
                      {row.source}
                    </td>
                    <td className="py-3 text-slate-200 max-w-[400px] truncate" title={row.content}>
                      {row.content}
                    </td>
                    <td className="py-3 text-right font-mono-nums text-xs text-slate-500">
                      {isNoise ? "— (noise)" : row.expected_behavioral_trigger || "—"}
                    </td>
                    <td className="py-3 text-right font-mono-nums text-xs text-slate-500">
                      {result ? (result.actual_trigger || "—") : "—"}
                    </td>
                    <td className="py-3 text-right">
                      {result ? (
                        result.passed ? (
                          <span className="px-2 py-0.5 rounded bg-emerald-900/50 text-emerald-400 text-[10px] border border-emerald-500/20">
                            PASS
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded bg-rose-900/50 text-rose-400 text-[10px] border border-rose-500/20">
                            FAIL
                          </span>
                        )
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-500 text-[10px]">
                          Untested
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
              {goldenRows.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-slate-500">
                    No golden rows found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Category summary table */}
      {categorySummary.length > 0 && (
        <div className="card p-5">
          <div className="font-semibold text-slate-100 mb-3">Golden Test Results by Category</div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm border-collapse">
              <thead>
                <tr className="text-slate-500 uppercase text-[10px] tracking-wider">
                  <th className="pb-3">Category</th>
                  <th className="pb-3 text-right">Passed</th>
                  <th className="pb-3 text-right">Failed</th>
                  <th className="pb-3 text-right">Total</th>
                  <th className="pb-3 text-right">Pass Rate</th>
                </tr>
              </thead>
              <tbody>
                {categorySummary.map((s) => (
                  <tr key={s.category_id} className="border-b border-slate-800/50">
                    <td className="py-3 text-slate-300">{s.category_name}</td>
                    <td className="py-3 text-right font-mono-nums text-emerald-400">{s.pass}</td>
                    <td className="py-3 text-right font-mono-nums text-rose-400">{s.fail}</td>
                    <td className="py-3 text-right font-mono-nums text-slate-400">{s.total}</td>
                    <td className="py-3 text-right font-mono-nums font-bold">
                      {(s.pass_rate * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
