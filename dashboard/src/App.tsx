import { useState, useEffect, useRef, useCallback } from 'react';
import axios from 'axios';
import Markdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  Shield,
  Activity,
  Microscope,
  Menu,
  X,
  Terminal,
  ExternalLink,
  ArrowRight,
  RefreshCw,
  Database,
  Brain,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlobeView } from './components/GlobeView';
import { ThreatMatrix } from './components/ThreatMatrix';
import type { Threat } from './components/ThreatMatrix';

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000/api";

export default function App() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedThreat, setSelectedThreat] = useState<Threat | null>(null);
  const [detail, setDetail] = useState<any>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [report, setReport] = useState<string | null>(null);
  const [filter, setFilter] = useState<'SUSPICIOUS' | 'SAFE'>('SUSPICIOUS');
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [activePage, setActivePage] = useState('ov');
  const [terminalOpen, setTerminalOpen] = useState(false);
  const [threatPanelOpen, setThreatPanelOpen] = useState(true);

  // Ref to avoid stale closure in interval
  const selectedThreatRef = useRef(selectedThreat);
  selectedThreatRef.current = selectedThreat;

  // -- Data Fetching --
  const fetchData = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/threats`);
      setData(res.data);
      // Don't auto-select — let user click to open case analysis
    } catch (err) {
      console.error("Failed to fetch data", err);
    } finally {
      setLoading(false);
    }
  }, []);

  const fetchReport = async () => {
    try {
      const res = await axios.get(`${API_BASE}/reports/master`);
      setReport(res.data.content);
    } catch {
      setReport("Report not available yet. Run the pipeline first to generate a forensic report.");
    }
  };

  const runPipeline = async () => {
    setPipelineRunning(true);
    try {
      await axios.post(`${API_BASE}/pipeline/run`);
      // Poll for completion instead of fixed timeout
      const pollInterval = setInterval(async () => {
        try {
          const status = await axios.get(`${API_BASE}/status`);
          const lastUpdated = status.data.last_updated;
          if (lastUpdated && Date.now() / 1000 - lastUpdated < 10) {
            clearInterval(pollInterval);
            fetchData();
            setPipelineRunning(false);
          }
        } catch { /* keep polling */ }
      }, 5000);
      // Safety timeout: stop polling after 10 minutes
      setTimeout(() => {
        clearInterval(pollInterval);
        setPipelineRunning(false);
        fetchData();
      }, 600000);
    } catch {
      setPipelineRunning(false);
    }
  };

  // -- Effects --
  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, [fetchData]);

  useEffect(() => {
    if (selectedThreat) {
      axios.get(`${API_BASE}/edits/detail`, {
        params: { user: selectedThreat.user, title: selectedThreat.title }
      }).then(res => setDetail(res.data))
        .catch(() => setDetail(null));
    }
  }, [selectedThreat]);

  // Auto-fetch report when switching to Forensic Lab
  useEffect(() => {
    if (activePage === 'fl' && !report) fetchReport();
  }, [activePage]);

  // -- Derived State --
  const filteredThreats = data ? data.top_threats.filter((t: any) => {
    if (filter === 'SUSPICIOUS') return t.action.includes('BLOCK') || t.action.includes('FLAG') || t.action.includes('REVIEW');
    if (filter === 'SAFE') return !t.action.includes('BLOCK') && !t.action.includes('FLAG') && !t.action.includes('REVIEW');
    return true;
  }) : [];

  // Distribution keys match actual JSON: "BLOCK", "FLAG", "REVIEW", "SAFE" (no emoji prefix)
  const activeThreats = data
    ? (data.distribution['BLOCK'] || 0) + (data.distribution['FLAG'] || 0)
    : 0;

  // Pre-compute filter counts
  const suspCount = data ? data.top_threats.filter((t: any) =>
    t.action.includes('BLOCK') || t.action.includes('FLAG') || t.action.includes('REVIEW')
  ).length : 0;
  const safeCount = data ? data.top_threats.length - suspCount : 0;

  // Compute AI confidence from data statistics
  const aiConfidence = data?.statistics?.avg_uncertainty != null
    ? `${Math.round((1 - data.statistics.avg_uncertainty) * 100)}%`
    : 'N/A';

  // -- Loading State --
  if (loading && !data) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-background text-cyan-400 font-mono">
        <RefreshCw className="animate-spin mr-3" /> INITIALIZING SYSTEMS...
      </div>
    );
  }

  if (!data) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-background text-red-400 font-mono gap-4">
        <Shield size={48} />
        <p>Failed to connect to API.</p>
        <button onClick={fetchData} className="px-4 py-2 bg-cyan-500 text-black rounded-lg font-bold">
          RETRY
        </button>
      </div>
    );
  }

  // -- Helper: strip wiki markup for readable display --
  const stripMarkup = (text: string) => {
    if (!text) return '';
    return text
      .replace(/https?:\/\/\S+/g, '')           // URLs
      .replace(/\{\{[^}]*\}\}/g, '')            // {{templates}}
      .replace(/\[\[(?:[^|\]]*\|)?([^\]]*)\]\]/g, '$1') // [[links]] -> display text
      .replace(/<[^>]+>/g, '')                   // <html tags>
      .replace(/[{}\[\]|='#*]/g, '')             // leftover markup chars
      .replace(/\s+/g, ' ')                      // collapse whitespace
      .trim();
  };

  // -- Helper: word-level diff using LCS (Longest Common Subsequence) --
  const wordDiff = (removed: string, added: string): { removedParts: {text: string, changed: boolean}[], addedParts: {text: string, changed: boolean}[] } => {
    const rWords = removed.split(/\s+/).filter(Boolean);
    const aWords = added.split(/\s+/).filter(Boolean);

    // Build LCS table
    const m = rWords.length, n = aWords.length;
    const dp: number[][] = Array.from({length: m + 1}, () => Array(n + 1).fill(0));
    for (let i = 1; i <= m; i++)
      for (let j = 1; j <= n; j++)
        dp[i][j] = rWords[i-1] === aWords[j-1] ? dp[i-1][j-1] + 1 : Math.max(dp[i-1][j], dp[i][j-1]);

    // Backtrack to find common words
    const rCommon = new Set<number>();
    const aCommon = new Set<number>();
    let i = m, j = n;
    while (i > 0 && j > 0) {
      if (rWords[i-1] === aWords[j-1]) { rCommon.add(i-1); aCommon.add(j-1); i--; j--; }
      else if (dp[i-1][j] > dp[i][j-1]) i--;
      else j--;
    }

    return {
      removedParts: rWords.map((w, idx) => ({ text: w + ' ', changed: !rCommon.has(idx) })),
      addedParts: aWords.map((w, idx) => ({ text: w + ' ', changed: !aCommon.has(idx) })),
    };
  };

  // -- Helper: format signal for display --
  const formatSignal = (val: any, suffix = '%') => {
    if (val == null || val === '') return 'N/A';
    const num = Number(val);
    return isNaN(num) ? String(val) : `${num.toFixed(0)}${suffix}`;
  };

  // -- AI justification text based on actual signals --
  const getJustification = (threat: Threat) => {
    const s = threat.signals;
    if (s.llm === 'VANDALISM') return "LLM semantic analysis classifies this edit as VANDALISM with high confidence. Content shows clear signs of malicious modification.";
    if (s.llm === 'SUSPICIOUS') return "LLM flags suspicious patterns. Combined with other signals, this edit warrants human review for potential misinformation.";
    if (s.rule > 3) return "Rule engine detected structural anomalies: blanking, large deletions, or profanity. Heuristic signals triggered.";
    if (s.nlp > 5) return "NLP analysis detected content anomalies: external link injection, citation stripping, or named entity tampering.";
    if (s.anomaly > 80) return "Isolation Forest flagged this as a multivariate outlier. The combination of features is statistically anomalous.";
    return "Standard verification path. No high-confidence signals triggered. Edit appears benign based on multi-signal fusion.";
  };

  // -- Main Render --
  return (
    <div className="h-screen w-screen flex bg-background overflow-hidden text-gray-200">
      {/* Sidebar */}
      <motion.nav
        initial={false}
        animate={{ width: sidebarOpen ? 260 : 80 }}
        className="h-full border-r border-white/5 bg-[#0f0f13] flex flex-col z-50 p-4 shrink-0"
      >
        <div className="flex items-center gap-3 mb-12 px-2">
          <div className="w-10 h-10 rounded-lg bg-cyan-500 flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.5)] cursor-pointer" onClick={() => setSidebarOpen(!sidebarOpen)}>
            <Shield size={22} className="text-white" />
          </div>
          {sidebarOpen && <span className="font-bold tracking-tight text-white text-lg">WIKI-STREAM</span>}
        </div>

        <div className="flex-1 flex flex-col gap-1">
          {[
            { id: 'ov', label: 'Overview', icon: Activity },
            { id: 'fl', label: 'Forensic Lab', icon: Microscope },
          ].map((item) => {
            const isActive = activePage === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActivePage(item.id)}
                title={!sidebarOpen ? item.label : undefined}
                className={`w-full flex items-center gap-4 px-3 py-3.5 rounded-xl transition-all duration-200 group ${
                  isActive
                    ? 'bg-cyan-500/15 text-cyan-400 shadow-[inset_0_0_20px_rgba(6,182,212,0.1)]'
                    : 'text-gray-500 hover:bg-white/5 hover:text-gray-300'
                }`}
              >
                <item.icon size={22} className={isActive ? 'text-cyan-400' : ''} />
                {sidebarOpen && <span className={`text-sm font-medium ${isActive ? 'text-cyan-400' : ''}`}>{item.label}</span>}
                {sidebarOpen && isActive && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(6,182,212,0.8)]" />}
              </button>
            );
          })}
        </div>

        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-3.5 rounded-xl hover:bg-white/10 text-gray-400 hover:text-white mt-auto flex items-center justify-center transition-colors"
          title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          {sidebarOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </motion.nav>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        {/* Top Header */}
        <header className="h-20 border-b border-white/5 flex items-center justify-between px-8 bg-background/50 backdrop-blur-md z-40 shrink-0">
          <div className="flex gap-12">
            {[
              { label: 'Total Edits', value: data.total, icon: Database },
              { label: 'Active Threats', value: activeThreats, icon: Shield, color: 'text-red-500' },
              { label: 'AI Confidence', value: aiConfidence, icon: Brain, color: 'text-purple-400' },
            ].map((stat, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-white/5"><stat.icon size={16} className="text-gray-400" /></div>
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-gray-500 font-bold">{stat.label}</div>
                  <div className={`font-mono font-bold ${stat.color || 'text-white'}`}>{stat.value}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-4">
            <button
              id="btn-trigger-pipeline"
              onClick={runPipeline}
              disabled={pipelineRunning}
              className={`px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-2 ${
                pipelineRunning
                  ? 'bg-gray-600 text-gray-400 cursor-not-allowed'
                  : 'bg-cyan-500 hover:bg-cyan-600 text-black shadow-[0_0_20px_rgba(6,182,212,0.3)]'
              }`}
            >
              <RefreshCw size={14} className={pipelineRunning ? 'animate-spin' : ''} />
              {pipelineRunning ? 'RUNNING...' : 'TRIGGER PIPELINE'}
            </button>
            <div className="px-3 py-1 bg-green-500/10 border border-green-500/20 rounded-full flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              <span className="text-[10px] font-bold text-green-500 uppercase tracking-widest">System Online</span>
            </div>
          </div>
        </header>

        {activePage === 'ov' ? (
          /* ── Overview: Globe + Threat Matrix ── */
          <div className="flex-1 flex overflow-hidden min-h-0">
            {/* 3D Globe Section */}
            <section className="flex-[3] relative overflow-hidden border-r border-white/5">
              <GlobeView safeCount={data.distribution['SAFE'] || 0} onThreatClick={(user, title) => {
                // Find threat in data and select it to open case analysis
                const found = data.top_threats.find((t: any) => t.user === user && t.title === title);
                if (found) setSelectedThreat(found);
              }} />

              {/* Terminal toggle button */}
              <button
                onClick={() => setTerminalOpen(!terminalOpen)}
                className="absolute bottom-6 left-6 z-10 p-2 rounded-lg bg-black/40 backdrop-blur-md border border-white/10 hover:bg-white/10 transition-colors"
                title={terminalOpen ? 'Hide logs' : 'Show logs'}
              >
                <Terminal size={16} className="text-cyan-400" />
              </button>

              {/* Live Terminal HUD */}
              {terminalOpen && (
                <div className="absolute bottom-16 left-6 w-[33%] h-48 glass-panel overflow-hidden flex flex-col z-10">
                  <div className="h-10 border-b border-white/5 bg-white/5 px-4 flex items-center gap-2">
                    <Terminal size={16} className="text-cyan-400" />
                    <span className="text-xs font-mono text-gray-400 tracking-wide">FORENSIC LOGS</span>
                  </div>
                  <div className="flex-1 p-4 font-mono text-xs text-gray-400 space-y-1.5 overflow-y-auto">
                    <p><span className="text-cyan-600">[INFO]</span> Connected to stream.wikimedia.org...</p>
                    <p><span className="text-cyan-600">[INFO]</span> Analyzing {data.total} edits across bipartite graph.</p>
                    <p><span className="text-purple-600">[DS]</span> Dempster-Shafer fusion: {data.statistics?.high_conflict_edits || 0} high-conflict edits detected.</p>
                    <p><span className="text-yellow-600">[IF]</span> IsolationForest: anomaly detection on {data.total} feature vectors.</p>
                    <p><span className="text-cyan-600">[INFO]</span> Avg uncertainty width: {data.statistics?.avg_uncertainty?.toFixed(3) || 'N/A'}</p>
                  </div>
                </div>
              )}
            </section>

            {/* Threat Matrix toggle button (when panel hidden) */}
            {!threatPanelOpen && (
              <button
                onClick={() => setThreatPanelOpen(true)}
                className="w-10 shrink-0 flex items-center justify-center bg-[#0c0c10] border-l border-white/5 hover:bg-white/5 transition-colors"
                title="Show Threat Matrix"
              >
                <Menu size={16} className="text-cyan-400" />
              </button>
            )}

            {/* Threat Matrix Feed */}
            {threatPanelOpen && (<section className="flex-[2] flex flex-col p-6 bg-[#0c0c10] overflow-hidden">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-lg font-bold flex items-center gap-2">
                  Threat Matrix <span className="text-xs bg-white/10 px-2 py-0.5 rounded-md text-gray-400">LIVE</span>
                </h2>
                <button onClick={() => setThreatPanelOpen(false)} className="p-1.5 hover:bg-white/10 rounded-lg transition-colors" title="Hide panel">
                  <ArrowRight size={16} className="text-gray-400" />
                </button>
              </div>

              {/* Filter Tabs */}
              <div className="flex gap-2 mb-4 shrink-0">
                {(['SUSPICIOUS', 'SAFE'] as const).map((f) => {
                  const count = f === 'SUSPICIOUS' ? suspCount : safeCount;
                  const isActive = filter === f;
                  return (
                    <button
                      key={f}
                      onClick={() => setFilter(f)}
                      className={`flex-1 py-2.5 text-xs font-bold rounded-lg transition-all duration-200 tracking-wide ${
                        isActive
                          ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 shadow-[0_0_12px_rgba(6,182,212,0.15)]'
                          : 'bg-white/5 text-gray-500 border border-white/5 hover:bg-white/10 hover:text-gray-300'
                      }`}
                    >
                      {f} ({count})
                    </button>
                  );
                })}
              </div>

              {/* Scrollable Threat List */}
              <div className="flex-1 overflow-y-auto min-h-0">
                {filteredThreats.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-gray-600 gap-3">
                    <Shield size={32} />
                    <p className="text-xs font-mono">No items in this category</p>
                  </div>
                ) : (
                  <ThreatMatrix
                    threats={filteredThreats}
                    onSelect={setSelectedThreat}
                    selectedUser={selectedThreat?.user}
                    selectedTitle={selectedThreat?.title}
                  />
                )}
              </div>
            </section>)}
          </div>
        ) : (
          /* ── Forensic Lab: Intelligence Report ── */
          <div className="flex-1 overflow-y-auto p-8">
            <div className="max-w-4xl mx-auto">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-cyan-400 flex items-center gap-3">
                  <Microscope size={22} /> Forensic Intelligence Report
                </h2>
                <button
                  onClick={() => { if (!report) fetchReport(); }}
                  className="px-4 py-2 text-xs font-bold rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 hover:bg-cyan-500/30 transition-all flex items-center gap-2"
                >
                  <RefreshCw size={14} /> Reload Report
                </button>
              </div>

              {/* Methodology Summary */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                {[
                  { label: 'Fusion Method', value: 'Dempster-Shafer', color: 'text-green-400' },
                  { label: 'Anomaly Detection', value: 'Isolation Forest', color: 'text-yellow-400' },
                  { label: 'Reputation Model', value: 'Beta-Bayesian', color: 'text-blue-400' },
                ].map((m, i) => (
                  <div key={i} className="p-4 rounded-xl bg-white/5 border border-white/10">
                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-1">{m.label}</div>
                    <div className={`font-mono font-bold text-sm ${m.color}`}>{m.value}</div>
                  </div>
                ))}
              </div>

              {/* Stats Cards */}
              <div className="grid grid-cols-4 gap-4 mb-6">
                {[
                  { label: 'Total Edits', value: data.total, color: 'text-white' },
                  { label: 'Blocked', value: data.distribution['BLOCK'] || 0, color: 'text-red-400' },
                  { label: 'Flagged', value: data.distribution['FLAG'] || 0, color: 'text-orange-400' },
                  { label: 'Under Review', value: data.distribution['REVIEW'] || 0, color: 'text-yellow-400' },
                ].map((s, i) => (
                  <div key={i} className="p-4 rounded-xl bg-white/5 border border-white/10 text-center">
                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-1">{s.label}</div>
                    <div className={`font-mono font-bold text-2xl ${s.color}`}>{s.value}</div>
                  </div>
                ))}
              </div>

              {/* Full Report */}
              <div className="rounded-xl bg-black/40 border border-white/10 p-6">
                <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-4">Full Forensic Report</div>
                {report ? (
                  <div
                    className="prose prose-invert prose-sm max-w-none prose-headings:text-cyan-400 prose-h1:text-xl prose-h2:text-lg prose-h3:text-base prose-strong:text-white prose-td:text-gray-300 prose-th:text-gray-400 prose-a:text-cyan-400 [&_td]:py-2 [&_th]:py-2"
                    ref={(el) => {
                      if (!el) return;
                      // Color-code table cells after render
                      el.querySelectorAll('td').forEach((td) => {
                        const t = td.textContent?.trim() || '';
                        if (t === 'BLOCK') { td.style.color = '#f87171'; td.style.fontWeight = 'bold'; }
                        else if (t === 'FLAG') { td.style.color = '#fb923c'; td.style.fontWeight = 'bold'; }
                        else if (t === 'REVIEW') { td.style.color = '#facc15'; td.style.fontWeight = 'bold'; }
                        else if (t === 'SAFE') { td.style.color = '#4ade80'; td.style.fontWeight = 'bold'; }
                      });
                    }}
                  >
                    <Markdown remarkPlugins={[remarkGfm]}>{report}</Markdown>
                  </div>
                ) : (
                  <div className="text-gray-500 text-sm">
                    <p>Loading report...</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Case Analysis — Slide-over panel */}
        <AnimatePresence>
          {detail && selectedThreat && (
            <>
              {/* Backdrop */}
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setDetail(null)}
                className="absolute inset-0 z-[80] bg-black/40 backdrop-blur-sm"
                style={{ top: '5rem' }}
              />
              {/* Panel */}
              <motion.div
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ type: 'spring', damping: 30, stiffness: 300 }}
                className="absolute right-0 bottom-0 z-[90] w-[900px] max-w-[95vw] bg-[#0c0c10] border-l border-cyan-500/20 shadow-[-10px_0_40px_rgba(0,0,0,0.6)] overflow-y-auto"
                style={{ top: '5rem' }}
              >
                {/* Header */}
                <div className="flex justify-between items-center px-6 py-3 bg-cyan-500/10 border-b border-white/5 shrink-0">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <Microscope size={16} className="text-cyan-400" />
                    Case Analysis
                  </h3>
                  <button onClick={() => setDetail(null)} className="p-1.5 hover:bg-white/10 rounded-lg transition-colors">
                    <X size={16} />
                  </button>
                </div>

                {/* Scrollable Content */}
                <div className="overflow-y-auto px-6 py-4 space-y-4">
                  {/* Title + Verdict */}
                  <div>
                    <div className="text-cyan-400 font-bold text-sm mb-1">{selectedThreat.title}</div>
                    <div className="flex items-center gap-3">
                      <span className="text-blue-400 font-mono text-xs">{selectedThreat.user}</span>
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold border ${
                        selectedThreat.action.includes('BLOCK') ? 'text-red-400 border-red-500/30 bg-red-500/10' :
                        selectedThreat.action.includes('FLAG') ? 'text-orange-400 border-orange-500/30 bg-orange-500/10' :
                        selectedThreat.action.includes('REVIEW') ? 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10' :
                        'text-green-400 border-green-500/30 bg-green-500/10'
                      }`}>
                        {selectedThreat.action} — {selectedThreat.score.toFixed(1)}%
                      </span>
                    </div>
                  </div>

                  {/* AI Justification */}
                  <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 text-xs leading-relaxed text-purple-200 flex gap-3">
                    <Brain className="shrink-0 mt-0.5" size={16} />
                    <span>{getJustification(selectedThreat)}</span>
                  </div>

                  {/* Signals Grid */}
                  <div>
                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-2">Forensic Signals</div>
                    <div className="grid grid-cols-4 gap-2">
                      {[
                        { label: 'RULE', value: formatSignal(selectedThreat.signals.rule, ''), color: 'text-cyan-400' },
                        { label: 'NLP', value: formatSignal(selectedThreat.signals.nlp, ''), color: 'text-orange-400' },
                        { label: 'LLM', value: selectedThreat.signals.llm || 'N/A', color: 'text-purple-400' },
                        { label: 'REP', value: formatSignal(selectedThreat.signals.reputation), color: 'text-blue-400' },
                      ].map((s, i) => (
                        <div key={i} className="p-2.5 rounded-lg bg-white/5 border border-white/10 text-center">
                          <div className="text-[10px] text-gray-500 mb-0.5">{s.label}</div>
                          <div className={`font-mono font-bold text-sm ${s.color}`}>{s.value}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* DS Evidence */}
                  <div>
                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-2">Dempster-Shafer Evidence</div>
                    <div className="grid grid-cols-3 gap-2">
                      {[
                        { label: 'BELIEF', value: `${(selectedThreat.ds_belief * 100).toFixed(1)}%`, color: 'text-green-400' },
                        { label: 'PLAUSIBILITY', value: `${(selectedThreat.ds_plausibility * 100).toFixed(1)}%`, color: 'text-yellow-400' },
                        { label: 'CONFLICT (k)', value: `${(selectedThreat.ds_conflict * 100).toFixed(1)}%`, color: 'text-red-400' },
                      ].map((s, i) => (
                        <div key={i} className="p-2.5 rounded-lg bg-white/5 border border-white/10 text-center">
                          <div className="text-[10px] text-gray-500 mb-0.5">{s.label}</div>
                          <div className={`font-mono font-bold text-sm ${s.color}`}>{s.value}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Detection Flags */}
                  {detail.nlp_notes && (
                    <div>
                      <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-2">Detection Flags</div>
                      <div className="flex flex-wrap gap-1.5">
                        {detail.nlp_notes.split(';').filter(Boolean).map((f: string, i: number) => (
                          <span key={i} className="px-2 py-1 bg-red-500/15 border border-red-500/30 text-red-400 text-[10px] font-bold rounded-md">{f.trim()}</span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Diff Viewer — word-level highlighting */}
                  <div>
                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-2">Diff Viewer</div>
                    {(() => {
                      const cleanR = stripMarkup(detail.diff_removed);
                      const cleanA = stripMarkup(detail.diff_added);
                      if (!cleanR && !cleanA) return <div className="text-gray-600 italic text-xs">No diff content available</div>;
                      const diff = wordDiff(cleanR, cleanA);
                      return (
                        <div className="p-4 rounded-xl bg-black/50 border border-white/10 text-[13px] leading-6 space-y-3">
                          {cleanR && (
                            <div className="overflow-y-auto border-l-2 border-red-500/30 pl-3">
                              <span className="text-red-500 font-bold text-[10px] uppercase">Removed</span>
                              <p className="mt-1 text-gray-400">
                                {diff.removedParts.map((p, i) =>
                                  p.changed
                                    ? <span key={i} className="bg-red-500/30 text-red-300 rounded px-0.5">{p.text}</span>
                                    : <span key={i}>{p.text}</span>
                                )}
                              </p>
                            </div>
                          )}
                          {cleanA && (
                            <div className="overflow-y-auto border-l-2 border-green-500/30 pl-3">
                              <span className="text-green-500 font-bold text-[10px] uppercase">Added</span>
                              <p className="mt-1 text-gray-400">
                                {diff.addedParts.map((p, i) =>
                                  p.changed
                                    ? <span key={i} className="bg-green-500/30 text-green-300 rounded px-0.5">{p.text}</span>
                                    : <span key={i}>{p.text}</span>
                                )}
                              </p>
                            </div>
                          )}
                        </div>
                      );
                    })()}
                  </div>
                </div>

                {/* Actions */}
                <div className="px-6 py-4 border-t border-white/5 flex gap-3">
                  <button className="flex-1 bg-red-500 hover:bg-red-600 text-white font-bold py-2.5 rounded-xl transition-all text-sm">
                    BLOCK USER
                  </button>
                  <a
                    href={detail.wiki_url || `https://en.wikipedia.org/wiki/${encodeURIComponent(selectedThreat.title)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2.5 bg-white/5 hover:bg-white/10 rounded-xl transition-all flex items-center gap-2 text-xs text-gray-400"
                  >
                    <ExternalLink size={14} /> View on Wikipedia
                  </a>
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>

      </main>
    </div>
  );
}
