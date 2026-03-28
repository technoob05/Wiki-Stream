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
  BarChart3,
  Download,
  Zap,
  Fingerprint,
  AlertTriangle,
  Clock,
  Keyboard,
  GitBranch,
  Timer,
  Maximize,
  Minimize,
  Copy,
  Check,
  Command,
  Settings as SettingsIcon,
  Table2,
  Volume2,
  VolumeX,
  Bookmark,
  BookmarkCheck,
  Eye,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { GlobeView } from './components/GlobeView';
import { ThreatMatrix } from './components/ThreatMatrix';
import { AnalyticsView } from './components/AnalyticsView';
import { SignalRadar } from './components/SignalRadar';
import { StatusBar } from './components/StatusBar';
import { ActivityTicker } from './components/ActivityTicker';
import { Sparkline } from './components/Sparkline';
import { MassSourceChart } from './components/MassSourceChart';
import { PignisticGauge } from './components/PignisticGauge';
import { CommandPalette } from './components/CommandPalette';
import { PipelineProgress } from './components/PipelineProgress';
import { ThreatTimeline } from './components/ThreatTimeline';
import { NetworkGraph } from './components/NetworkGraph';
import { DataTable } from './components/DataTable';
import { EvidenceFlow } from './components/EvidenceFlow';
import { SettingsPanel } from './components/SettingsPanel';
import { NotificationCenter } from './components/NotificationCenter';
import { Confetti } from './components/Confetti';
import { ContextMenu } from './components/ContextMenu';
import { OnboardingTour } from './components/OnboardingTour';
import { ShareButton } from './components/ShareButton';
import { ParticleField } from './components/ParticleField';
import { MouseSpotlight } from './components/MouseSpotlight';
import { MatrixRain } from './components/MatrixRain';
import { TiltCard } from './components/TiltCard';
import type { AppNotification } from './components/NotificationCenter';
import type { ContextMenuItem } from './components/ContextMenu';
import type { Settings } from './components/SettingsPanel';
import type { Action } from './components/CommandPalette';
import type { Threat } from './components/ThreatMatrix';

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

// -- Notification Toast System --
interface Toast {
  id: number;
  message: string;
  type: 'threat' | 'info' | 'success';
  exiting?: boolean;
}

let toastId = 0;

// -- Animated Number Counter --
const AnimatedNumber: React.FC<{ value: number; className?: string }> = ({ value, className }) => {
  const [display, setDisplay] = useState(0);
  const prev = useRef(0);

  useEffect(() => {
    const start = prev.current;
    const diff = value - start;
    if (diff === 0) return;
    const duration = 600;
    const startTime = performance.now();
    const animate = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      setDisplay(Math.round(start + diff * eased));
      if (progress < 1) requestAnimationFrame(animate);
      else prev.current = value;
    };
    requestAnimationFrame(animate);
  }, [value]);

  return <span className={className}>{display.toLocaleString()}</span>;
};

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
  const [apiError, setApiError] = useState<string | null>(null);
  const [toasts, setToasts] = useState<Toast[]>([]);
  const [bootComplete, setBootComplete] = useState(false);
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [lastDataHash, setLastDataHash] = useState('');
  const [cmdPaletteOpen, setCmdPaletteOpen] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [settings, setSettings] = useState<Settings>({
    accentColor: '#06b6d4',
    soundEnabled: false,
    scanlines: true,
    density: 'normal',
    autoRefresh: true,
    refreshInterval: 10000,
  });
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [confettiActive, setConfettiActive] = useState(false);
  const [contextMenu, setContextMenu] = useState<{ open: boolean; x: number; y: number; threat: Threat | null }>({ open: false, x: 0, y: 0, threat: null });
  const [bookmarks, setBookmarks] = useState<Set<string>>(() => {
    try { return new Set(JSON.parse(localStorage.getItem('wikistream_bookmarks') || '[]')); } catch { return new Set(); }
  });
  const notifIdRef = useRef(0);
  const pipelineIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const pipelineTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [sparkHistory, setSparkHistory] = useState<{ total: number[]; threats: number[]; confidence: number[] }>({
    total: [], threats: [], confidence: [],
  });

  const selectedThreatRef = useRef(selectedThreat);
  selectedThreatRef.current = selectedThreat;

  // -- Bookmark helpers --
  const toggleBookmark = useCallback((threat: Threat) => {
    const key = `${threat.user}::${threat.title}`;
    setBookmarks(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key); else next.add(key);
      localStorage.setItem('wikistream_bookmarks', JSON.stringify([...next]));
      return next;
    });
  }, []);

  const isBookmarked = useCallback((threat: Threat) => bookmarks.has(`${threat.user}::${threat.title}`), [bookmarks]);

  // -- Toast + Notification System --
  const addToast = useCallback((message: string, type: Toast['type'] = 'info') => {
    const id = ++toastId;
    setToasts(prev => [...prev.slice(-4), { id, message, type }]);
    // Also push to notification center
    const nid = ++notifIdRef.current;
    setNotifications(prev => [...prev.slice(-49), { id: nid, message, type, time: new Date(), read: false }]);
    setTimeout(() => {
      setToasts(prev => prev.map(t => t.id === id ? { ...t, exiting: true } : t));
      setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 300);
    }, 4000);
  }, []);

  // -- Data Fetching --
  const fetchData = useCallback(async () => {
    try {
      const res = await axios.get(`${API_BASE}/threats`, { timeout: 5000 });
      setData(res.data);
      setApiError(null);

      // Track sparkline history
      const d = res.data;
      const threats = (d.distribution?.['BLOCK'] || 0) + (d.distribution?.['FLAG'] || 0);
      const conf = d.statistics?.avg_uncertainty != null ? Math.round((1 - d.statistics.avg_uncertainty) * 100) : 0;
      setSparkHistory(prev => ({
        total: [...prev.total.slice(-19), d.total || 0],
        threats: [...prev.threats.slice(-19), threats],
        confidence: [...prev.confidence.slice(-19), conf],
      }));

      // Notify on new high-severity threats
      const hash = JSON.stringify(res.data.distribution);
      if (lastDataHash && hash !== lastDataHash) {
        const newBlocks = res.data.distribution?.['BLOCK'] || 0;
        if (newBlocks > 0) {
          addToast(`${newBlocks} BLOCK-level threats detected`, 'threat');
          // Play alert sound if enabled
          if (settings.soundEnabled) {
            try {
              const ctx = new AudioContext();
              const osc = ctx.createOscillator();
              const gain = ctx.createGain();
              osc.connect(gain);
              gain.connect(ctx.destination);
              osc.frequency.value = 800;
              gain.gain.value = 0.1;
              osc.start();
              gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
              osc.stop(ctx.currentTime + 0.3);
            } catch {}
          }
        }
      }
      setLastDataHash(hash);
    } catch (err: any) {
      if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        setApiError('Connection timed out. Is the API server running?');
      } else if (err.response?.status === 404) {
        setApiError('No intelligence data found. Run the pipeline first to generate reports.');
      } else if (!err.response) {
        setApiError(`Cannot reach API at ${API_BASE}. Start the server: python experiments/api_service.py`);
      } else {
        setApiError(`API error: ${err.response?.status} — ${err.response?.statusText}`);
      }
      console.error("Failed to fetch data", err);
    } finally {
      setLoading(false);
    }
  }, [lastDataHash, addToast]);

  const fetchReport = async () => {
    try {
      const res = await axios.get(`${API_BASE}/reports/master`);
      setReport(res.data.content);
    } catch {
      setReport("Report not available yet. Run the pipeline first to generate a forensic report.");
    }
  };

  const cancelPipeline = () => {
    if (pipelineIntervalRef.current) clearInterval(pipelineIntervalRef.current);
    if (pipelineTimeoutRef.current) clearTimeout(pipelineTimeoutRef.current);
    pipelineIntervalRef.current = null;
    pipelineTimeoutRef.current = null;
    setPipelineRunning(false);
    addToast('Pipeline monitoring cancelled.', 'info');
  };

  const runPipeline = async () => {
    setPipelineRunning(true);
    addToast('Pipeline started — analyzing incoming edits...', 'info');
    try {
      await axios.post(`${API_BASE}/pipeline/run`);
      pipelineIntervalRef.current = setInterval(async () => {
        try {
          const status = await axios.get(`${API_BASE}/status`);
          const lastUpdated = status.data.last_updated;
          if (lastUpdated && Date.now() / 1000 - lastUpdated < 10) {
            if (pipelineIntervalRef.current) clearInterval(pipelineIntervalRef.current);
            if (pipelineTimeoutRef.current) clearTimeout(pipelineTimeoutRef.current);
            fetchData();
            setPipelineRunning(false);
            addToast('Pipeline complete! Intelligence updated.', 'success');
            setConfettiActive(true);
            setTimeout(() => setConfettiActive(false), 4000);
          }
        } catch { /* keep polling */ }
      }, 5000);
      pipelineTimeoutRef.current = setTimeout(() => {
        if (pipelineIntervalRef.current) clearInterval(pipelineIntervalRef.current);
        setPipelineRunning(false);
        fetchData();
      }, 600000);
    } catch {
      setPipelineRunning(false);
      addToast('Pipeline failed to start.', 'threat');
    }
  };

  const exportData = () => {
    if (!data) return;
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `wikistream_intelligence_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    addToast('Intelligence data exported', 'success');
  };

  // -- Effects --
  useEffect(() => {
    // Minimum boot animation time = last line delay (1500ms) + animation (300ms) + buffer
    const t = setTimeout(() => setBootComplete(true), 1900);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    fetchData();
    if (!settings.autoRefresh && data) return;
    const interval = setInterval(fetchData, data ? settings.refreshInterval : 3000);
    return () => clearInterval(interval);
  }, [fetchData, !data, settings.autoRefresh, settings.refreshInterval]);

  useEffect(() => {
    if (selectedThreat) {
      axios.get(`${API_BASE}/edits/detail`, {
        params: { user: selectedThreat.user, title: selectedThreat.title }
      }).then(res => setDetail(res.data))
        .catch(() => setDetail(null));
    }
  }, [selectedThreat]);

  useEffect(() => {
    if (activePage === 'fl' && !report) fetchReport();
  }, [activePage]);

  // -- Dynamic Tab Title --
  useEffect(() => {
    if (!data) return;
    const blocks = data.distribution?.['BLOCK'] || 0;
    const flags = data.distribution?.['FLAG'] || 0;
    const total = blocks + flags;
    document.title = total > 0
      ? `(${total}) Wiki-Stream Intelligence`
      : 'Wiki-Stream Intelligence Dashboard';
  }, [data]);

  // -- Keyboard Shortcuts --
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Ctrl+K / Cmd+K for command palette
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setCmdPaletteOpen(o => !o);
        return;
      }
      if (e.key === 'Escape') {
        if (cmdPaletteOpen) { setCmdPaletteOpen(false); return; }
        if (showShortcuts) { setShowShortcuts(false); return; }
        if (detail) { setDetail(null); return; }
        if (fullscreen) { setFullscreen(false); return; }
      }
      if (e.key === '?' && !e.ctrlKey && !e.metaKey && !(e.target instanceof HTMLInputElement)) {
        setShowShortcuts(s => !s);
        return;
      }
      if (e.target instanceof HTMLInputElement) return;
      if (e.key === '1') setActivePage('ov');
      if (e.key === '2') setActivePage('an');
      if (e.key === '3') setActivePage('dt');
      if (e.key === '4') setActivePage('ng');
      if (e.key === '5') setActivePage('tl');
      if (e.key === '6') setActivePage('fl');
      if (e.key === 't') setTerminalOpen(t => !t);
      if (e.key === 'p' && !pipelineRunning) runPipeline();
      if (e.key === 'f') setFullscreen(f => !f);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [detail, pipelineRunning, showShortcuts, cmdPaletteOpen, fullscreen]);

  // -- Boot Sequence --
  useEffect(() => {
    const timer = setTimeout(() => setBootComplete(true), 2000);
    return () => clearTimeout(timer);
  }, []);

  // -- Derived State --
  const filteredThreats = data ? data.top_threats.filter((t: any) => {
    if (filter === 'SUSPICIOUS') return t.action.includes('BLOCK') || t.action.includes('FLAG') || t.action.includes('REVIEW');
    if (filter === 'SAFE') return !t.action.includes('BLOCK') && !t.action.includes('FLAG') && !t.action.includes('REVIEW');
    return true;
  }) : [];

  const activeThreats = data
    ? (data.distribution['BLOCK'] || 0) + (data.distribution['FLAG'] || 0)
    : 0;

  const suspCount = data ? data.top_threats.filter((t: any) =>
    t.action.includes('BLOCK') || t.action.includes('FLAG') || t.action.includes('REVIEW')
  ).length : 0;
  const safeCount = data ? data.top_threats.length - suspCount : 0;

  const aiConfidence = data?.statistics?.avg_uncertainty != null
    ? Math.round((1 - data.statistics.avg_uncertainty) * 100)
    : null;

  // -- Loading / Boot Sequence --
  if (loading || !bootComplete) {
    const bootLines = [
      { text: 'WIKI-STREAM INTELLIGENCE PLATFORM v2.0', delay: 0 },
      { text: 'Initializing Dempster-Shafer fusion engine...', delay: 200 },
      { text: 'Loading Isolation Forest anomaly detector...', delay: 400 },
      { text: 'Connecting to Wikimedia SSE stream...', delay: 600 },
      { text: 'Bootstrapping Beta-Bayesian reputation model...', delay: 800 },
      { text: 'Authenticating forensic pipeline modules...', delay: 1000 },
      { text: `Connecting to API: ${API_BASE}`, delay: 1200 },
      { text: 'SYSTEM READY.', delay: 1500 },
    ];

    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-background font-mono relative">
        <ParticleField />
        <div className="w-full max-w-lg space-y-1 px-8">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 rounded-lg bg-cyan-500 flex items-center justify-center shadow-[0_0_20px_rgba(6,182,212,0.5)] float-animation">
              <Shield size={22} className="text-white" />
            </div>
            <span className="font-bold text-lg tracking-tight holo-text">WIKI-STREAM</span>
          </div>
          {bootLines.map((line, i) => (
            <div
              key={i}
              className="boot-line text-xs"
              style={{ animationDelay: `${line.delay}ms`, color: i === bootLines.length - 1 ? '#22c55e' : '#06b6d4' }}
            >
              <span className="text-gray-600 mr-2">[{String(i).padStart(2, '0')}]</span>
              {line.text}
              {i === bootLines.length - 1 && <span className="cursor-blink ml-1" />}
            </div>
          ))}
          {/* Progress bar — fills over 1800ms matching full animation duration */}
          <div className="mt-6">
            <div className="h-px w-full bg-white/5 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-cyan-500 via-purple-500 to-cyan-400 rounded-full boot-progress" />
            </div>
            <div className="mt-2 flex items-center gap-2 text-gray-600 text-[10px]">
              <RefreshCw size={10} className="animate-spin" />
              {loading ? 'Establishing connection...' : 'Finalizing boot sequence...'}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-background text-red-400 font-mono gap-4">
        <Shield size={48} />
        <p className="text-lg font-bold">Failed to connect to API</p>
        <p className="text-sm text-gray-400 max-w-md text-center">
          {apiError || `Cannot reach ${API_BASE}. Make sure the backend is running.`}
        </p>
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <RefreshCw size={12} className="animate-spin" /> Auto-retrying every 3s...
        </div>
        <button onClick={fetchData} className="px-4 py-2 bg-cyan-500 text-black rounded-lg font-bold">
          RETRY NOW
        </button>
      </div>
    );
  }

  // -- Helpers --
  const stripMarkup = (text: string) => {
    if (!text) return '';
    return text
      .replace(/https?:\/\/\S+/g, '')
      .replace(/\{\{[^}]*\}\}/g, '')
      .replace(/\[\[(?:[^|\]]*\|)?([^\]]*)\]\]/g, '$1')
      .replace(/<[^>]+>/g, '')
      .replace(/[{}\[\]|='#*]/g, '')
      .replace(/\s+/g, ' ')
      .trim();
  };

  const wordDiff = (removed: string, added: string) => {
    const rWords = removed.split(/\s+/).filter(Boolean);
    const aWords = added.split(/\s+/).filter(Boolean);
    const m = rWords.length, n = aWords.length;
    const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));
    for (let i = 1; i <= m; i++)
      for (let j = 1; j <= n; j++)
        dp[i][j] = rWords[i - 1] === aWords[j - 1] ? dp[i - 1][j - 1] + 1 : Math.max(dp[i - 1][j], dp[i][j - 1]);
    const rCommon = new Set<number>();
    const aCommon = new Set<number>();
    let i = m, j = n;
    while (i > 0 && j > 0) {
      if (rWords[i - 1] === aWords[j - 1]) { rCommon.add(i - 1); aCommon.add(j - 1); i--; j--; }
      else if (dp[i - 1][j] > dp[i][j - 1]) i--;
      else j--;
    }
    return {
      removedParts: rWords.map((w, idx) => ({ text: w + ' ', changed: !rCommon.has(idx) })),
      addedParts: aWords.map((w, idx) => ({ text: w + ' ', changed: !aCommon.has(idx) })),
    };
  };

  const formatSignal = (val: any, suffix = '%') => {
    if (val == null || val === '') return 'N/A';
    const num = Number(val);
    return isNaN(num) ? String(val) : `${num.toFixed(0)}${suffix}`;
  };

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
      {/* Mouse spotlight effect */}
      <MouseSpotlight />

      {/* Confetti celebration */}
      <Confetti active={confettiActive} />

      {/* Onboarding Tour (first visit only) */}
      <OnboardingTour />

      {/* Right-click context menu */}
      <ContextMenu
        x={contextMenu.x}
        y={contextMenu.y}
        open={contextMenu.open}
        onClose={() => setContextMenu(c => ({ ...c, open: false }))}
        items={contextMenu.threat ? (() => { const ct = contextMenu.threat!; const bk = isBookmarked(ct); return [
          { label: 'View Case Analysis', icon: Eye, action: () => setSelectedThreat(ct) },
          { label: bk ? 'Remove Bookmark' : 'Bookmark Threat', icon: bk ? BookmarkCheck : Bookmark, action: () => { toggleBookmark(ct); addToast(bk ? 'Bookmark removed' : 'Threat bookmarked', 'success'); } },
          { label: 'Copy Evidence', icon: Copy, action: () => { navigator.clipboard.writeText(`${ct.action} | ${ct.title} | ${ct.user} | Score: ${ct.score.toFixed(1)}%`); addToast('Evidence copied', 'success'); } },
          { label: 'View on Wikipedia', icon: ExternalLink, separator: true, action: () => window.open(`https://en.wikipedia.org/wiki/${encodeURIComponent(ct.title)}`, '_blank') },
        ] as ContextMenuItem[]; })() : []}
      />

      {/* Scanline + Noise overlay (toggleable) */}
      {settings.scanlines && <div className="scanline-overlay" />}
      {settings.scanlines && <div className="noise-overlay" />}

      {/* Settings Panel */}
      <SettingsPanel
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        settings={settings}
        onChange={setSettings}
      />

      {/* Toast Notifications */}
      <div className="fixed top-24 right-6 z-[200] flex flex-col gap-2 pointer-events-none">
        <AnimatePresence>
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, x: 80, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 80, scale: 0.95 }}
              className={`pointer-events-auto px-4 py-3 rounded-xl border backdrop-blur-md shadow-xl flex items-center gap-3 text-xs font-bold ${
                toast.type === 'threat' ? 'bg-red-500/15 border-red-500/30 text-red-400' :
                toast.type === 'success' ? 'bg-green-500/15 border-green-500/30 text-green-400' :
                'bg-cyan-500/15 border-cyan-500/30 text-cyan-400'
              }`}
            >
              {toast.type === 'threat' && <AlertTriangle size={14} />}
              {toast.type === 'success' && <Zap size={14} />}
              {toast.type === 'info' && <Activity size={14} />}
              {toast.message}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Command Palette */}
      <CommandPalette
        open={cmdPaletteOpen}
        onClose={() => setCmdPaletteOpen(false)}
        actions={[
          { id: 'nav-overview', label: 'Go to Overview', description: 'Globe + Threat Matrix view', icon: Activity, category: 'Navigation', shortcut: '1', action: () => setActivePage('ov') },
          { id: 'nav-analytics', label: 'Go to Analytics', description: 'Charts and data analysis', icon: BarChart3, category: 'Navigation', shortcut: '2', action: () => setActivePage('an') },
          { id: 'nav-datatable', label: 'Go to Data Table', description: 'Sortable threat table with filters', icon: Table2, category: 'Navigation', shortcut: '3', action: () => setActivePage('dt') },
          { id: 'nav-network', label: 'Go to Network Graph', description: 'User-article relationship graph', icon: GitBranch, category: 'Navigation', shortcut: '4', action: () => setActivePage('ng') },
          { id: 'nav-timeline', label: 'Go to Timeline', description: 'Temporal threat density', icon: Timer, category: 'Navigation', shortcut: '5', action: () => setActivePage('tl') },
          { id: 'nav-forensic', label: 'Go to Forensic Lab', description: 'Intelligence report viewer', icon: Microscope, category: 'Navigation', shortcut: '6', action: () => setActivePage('fl') },
          { id: 'act-pipeline', label: 'Trigger Pipeline', description: 'Run the 7-stage analysis pipeline', icon: RefreshCw, category: 'Actions', shortcut: 'P', action: () => { if (!pipelineRunning) runPipeline(); } },
          { id: 'act-export', label: 'Export Intelligence Data', description: 'Download JSON intelligence report', icon: Download, category: 'Actions', action: exportData },
          { id: 'act-terminal', label: 'Toggle Terminal', description: 'Show/hide forensic logs', icon: Terminal, category: 'Actions', shortcut: 'T', action: () => setTerminalOpen(t => !t) },
          { id: 'act-fullscreen', label: 'Toggle Fullscreen', description: 'Expand content area', icon: Maximize, category: 'Actions', shortcut: 'F', action: () => setFullscreen(f => !f) },
          { id: 'act-settings', label: 'Settings', description: 'Accent color, sounds, density', icon: SettingsIcon, category: 'Actions', action: () => setSettingsOpen(true) },
          { id: 'act-shortcuts', label: 'Keyboard Shortcuts', description: 'View all shortcuts', icon: Keyboard, category: 'Help', shortcut: '?', action: () => setShowShortcuts(true) },
        ] as Action[]}
      />

      {/* Keyboard Shortcuts Modal */}
      <AnimatePresence>
        {showShortcuts && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setShowShortcuts(false)}
            className="fixed inset-0 z-[300] bg-black/60 backdrop-blur-sm flex items-center justify-center"
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={e => e.stopPropagation()}
              className="bg-[#0f0f13] border border-white/10 rounded-2xl p-6 w-[420px] shadow-2xl"
            >
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-white flex items-center gap-2">
                  <Keyboard size={16} className="text-cyan-400" /> Keyboard Shortcuts
                </h3>
                <button onClick={() => setShowShortcuts(false)} className="p-1 hover:bg-white/10 rounded-lg">
                  <X size={14} className="text-gray-400" />
                </button>
              </div>
              <div className="space-y-2">
                {[
                  { key: 'Ctrl+K', desc: 'Command palette' },
                  { key: '1', desc: 'Overview' },
                  { key: '2', desc: 'Analytics' },
                  { key: '3', desc: 'Data Table' },
                  { key: '4', desc: 'Network Graph' },
                  { key: '5', desc: 'Timeline' },
                  { key: '6', desc: 'Forensic Lab' },
                  { key: 'T', desc: 'Toggle terminal' },
                  { key: 'P', desc: 'Trigger pipeline' },
                  { key: 'F', desc: 'Toggle fullscreen' },
                  { key: 'Esc', desc: 'Close panel / modal' },
                  { key: '?', desc: 'Show shortcuts' },
                ].map((s, i) => (
                  <div key={i} className="flex items-center justify-between py-1.5">
                    <span className="text-xs text-gray-400">{s.desc}</span>
                    <kbd className="px-2.5 py-1 bg-white/5 border border-white/10 rounded-md text-[10px] font-mono text-cyan-400 font-bold">
                      {s.key}
                    </kbd>
                  </div>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.nav
        initial={false}
        animate={{ width: fullscreen ? 0 : sidebarOpen ? 260 : 80, opacity: fullscreen ? 0 : 1 }}
        className={`h-full border-r border-white/5 bg-[#0f0f13] flex flex-col z-50 p-4 shrink-0 ${fullscreen ? 'overflow-hidden pointer-events-none' : ''}`}
      >
        <div className="flex items-center gap-3 mb-10 px-2">
          <div className="w-10 h-10 rounded-lg bg-cyan-500 flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.5)] cursor-pointer" onClick={() => setSidebarOpen(!sidebarOpen)}>
            <Shield size={22} className="text-white" />
          </div>
          {sidebarOpen && (
            <div>
              <span className="font-bold tracking-tight text-white text-lg neon-text">WIKI-STREAM</span>
              <div className="text-[9px] text-cyan-500/60 font-mono tracking-widest">INTELLIGENCE v2.0</div>
            </div>
          )}
        </div>

        <div className="flex-1 flex flex-col gap-1">
          {[
            { id: 'ov', label: 'Overview', icon: Activity },
            { id: 'an', label: 'Analytics', icon: BarChart3 },
            { id: 'dt', label: 'Data Table', icon: Table2 },
            { id: 'ng', label: 'Network Graph', icon: GitBranch },
            { id: 'tl', label: 'Timeline', icon: Timer },
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
                {sidebarOpen && (
                  <span className={`text-sm font-medium animated-underline ${isActive ? 'text-cyan-400' : ''}`}>{item.label}</span>
                )}
                {sidebarOpen && isActive && <div className="ml-auto w-1.5 h-1.5 rounded-full bg-cyan-400 shadow-[0_0_6px_rgba(6,182,212,0.8)]" />}
              </button>
            );
          })}
        </div>

        {/* Mini Distribution */}
        {sidebarOpen && data && (
          <div className="px-2 mb-4">
            <div className="text-[9px] text-gray-600 font-bold uppercase tracking-widest mb-2">Distribution</div>
            <div className="space-y-1.5">
              {[
                { label: 'BLK', value: data.distribution['BLOCK'] || 0, color: '#ef4444' },
                { label: 'FLG', value: data.distribution['FLAG'] || 0, color: '#f97316' },
                { label: 'REV', value: data.distribution['REVIEW'] || 0, color: '#facc15' },
                { label: 'SAFE', value: data.distribution['SAFE'] || 0, color: '#22c55e' },
              ].map((item) => {
                const pct = data.total > 0 ? (item.value / data.total) * 100 : 0;
                return (
                  <div key={item.label} className="flex items-center gap-2">
                    <span className="text-[9px] font-mono text-gray-500 w-7">{item.label}</span>
                    <div className="flex-1 h-1 bg-white/5 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.8 }}
                        className="h-full rounded-full"
                        style={{ backgroundColor: item.color }}
                      />
                    </div>
                    <span className="text-[9px] font-mono text-gray-600 w-6 text-right">{item.value}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Sidebar footer */}
        <div className="space-y-1">
          <button
            onClick={() => setCmdPaletteOpen(true)}
            className="w-full flex items-center gap-4 px-3 py-2.5 rounded-xl text-gray-600 hover:bg-white/5 hover:text-gray-400 transition-colors"
            title="Command palette (Ctrl+K)"
          >
            <Command size={18} />
            {sidebarOpen && (
              <div className="flex-1 flex items-center justify-between">
                <span className="text-xs">Search</span>
                <kbd className="px-1.5 py-0.5 bg-white/5 border border-white/10 rounded text-[9px] font-mono text-gray-600">Ctrl+K</kbd>
              </div>
            )}
          </button>
          <button
            onClick={() => setSettingsOpen(true)}
            className="w-full flex items-center gap-4 px-3 py-2.5 rounded-xl text-gray-600 hover:bg-white/5 hover:text-gray-400 transition-colors"
            title="Settings"
          >
            <SettingsIcon size={18} />
            {sidebarOpen && <span className="text-xs">Settings</span>}
          </button>
          <button
            onClick={() => setShowShortcuts(true)}
            className="w-full flex items-center gap-4 px-3 py-2.5 rounded-xl text-gray-600 hover:bg-white/5 hover:text-gray-400 transition-colors"
            title="Keyboard shortcuts"
          >
            <Keyboard size={18} />
            {sidebarOpen && <span className="text-xs">Shortcuts</span>}
          </button>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="w-full p-3.5 rounded-xl hover:bg-white/10 text-gray-400 hover:text-white flex items-center justify-center transition-colors"
            title={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {sidebarOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </motion.nav>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden relative grid-bg">
        {/* Top Header */}
        <header className="h-20 border-b border-white/5 flex items-center justify-between px-8 bg-background/80 backdrop-blur-md z-40 shrink-0 data-stream-bg">
          <div className="flex gap-6">
            {[
              { label: 'Total Edits', value: data.total, icon: Database, animated: true, spark: sparkHistory.total, sparkColor: '#06b6d4' },
              { label: 'Active Threats', value: activeThreats, icon: Shield, color: 'text-red-500', animated: true, spark: sparkHistory.threats, sparkColor: '#ef4444' },
              { label: 'AI Confidence', value: aiConfidence != null ? `${aiConfidence}%` : 'N/A', icon: Brain, color: 'text-purple-400', spark: sparkHistory.confidence, sparkColor: '#a855f7' },
              { label: 'Entropy', value: data.statistics?.avg_deng_entropy?.toFixed(2) || 'N/A', icon: Fingerprint, color: 'text-blue-400' },
              { label: 'Blocked', value: data.distribution['BLOCK'] || 0, icon: AlertTriangle, color: 'text-red-400', animated: true },
            ].map((stat, i) => (
              <TiltCard key={i} intensity={6} glare={false} className="flex items-center gap-3 px-2 py-1 rounded-lg cursor-default">
                <div className="p-2 rounded-lg bg-white/5"><stat.icon size={16} className="text-gray-400" /></div>
                <div>
                  <div className="text-[10px] uppercase tracking-wider text-gray-500 font-bold">{stat.label}</div>
                  <div className="flex items-center gap-2">
                    <div className={`font-mono font-bold ${stat.color || 'text-white'}`}>
                      {stat.animated && typeof stat.value === 'number'
                        ? <AnimatedNumber value={stat.value} />
                        : stat.value}
                    </div>
                    {stat.spark && stat.spark.length > 1 && (
                      <Sparkline data={stat.spark} width={48} height={16} color={stat.sparkColor} />
                    )}
                  </div>
                </div>
              </TiltCard>
            ))}
          </div>

          <div className="flex items-center gap-3">
            {fullscreen && (
              <button
                onClick={() => setFullscreen(false)}
                className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-cyan-400 transition-all border border-white/5"
                title="Exit fullscreen (F)"
              >
                <Minimize size={14} />
              </button>
            )}
            <ShareButton data={data} addToast={addToast} />
            <NotificationCenter
              notifications={notifications}
              onClear={() => setNotifications([])}
              onMarkRead={(id) => setNotifications(prev => prev.map(n => n.id === id ? { ...n, read: true } : n))}
            />
            <button
              onClick={exportData}
              className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-400 hover:text-cyan-400 transition-all border border-white/5"
              title="Export intelligence data"
            >
              <Download size={14} />
            </button>
            <button
              id="btn-trigger-pipeline"
              onClick={pipelineRunning ? cancelPipeline : runPipeline}
              className={`px-4 py-2 text-xs font-bold rounded-lg transition-all flex items-center gap-2 ${
                pipelineRunning
                  ? 'bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/30'
                  : 'bg-cyan-500 hover:bg-cyan-600 text-black shadow-[0_0_20px_rgba(6,182,212,0.3)] ripple'
              }`}
            >
              <RefreshCw size={14} className={pipelineRunning ? 'animate-spin' : ''} />
              {pipelineRunning ? 'CANCEL' : 'TRIGGER PIPELINE'}
            </button>
            <div className="px-3 py-1 bg-green-500/10 border border-green-500/20 rounded-full flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500 pulse-ring" />
              <span className="text-[10px] font-bold text-green-500 uppercase tracking-widest">Live</span>
            </div>
            {/* Uptime */}
            <div className="text-[10px] text-gray-600 font-mono flex items-center gap-1.5">
              <Clock size={10} />
              {data.timestamp ? new Date(data.timestamp).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' }) : '--:--'}
            </div>
          </div>
        </header>

        {/* Pipeline Progress Tracker */}
        <AnimatePresence>
          {pipelineRunning && <PipelineProgress running={pipelineRunning} />}
        </AnimatePresence>

        <AnimatePresence mode="wait">
        {activePage === 'ov' ? (
          /* ── Overview: Globe + Threat Matrix ── */
          <motion.div key="ov" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }} className="flex-1 flex flex-col overflow-hidden min-h-0">
            <div className="flex-1 flex overflow-hidden min-h-0">
            {/* 3D Globe Section */}
            <section className="flex-[3] relative overflow-hidden border-r border-white/5">
              <GlobeView safeCount={data.distribution['SAFE'] || 0} onThreatClick={(user, title) => {
                const found = data.top_threats.find((t: any) => t.user === user && t.title === title);
                if (found) setSelectedThreat(found);
              }} />

              {/* Terminal toggle button */}
              <button
                onClick={() => setTerminalOpen(!terminalOpen)}
                className="absolute bottom-6 left-6 z-10 p-2 rounded-lg bg-black/40 backdrop-blur-md border border-white/10 hover:bg-white/10 transition-colors"
                title={terminalOpen ? 'Hide logs (T)' : 'Show logs (T)'}
              >
                <Terminal size={16} className="text-cyan-400" />
              </button>

              {/* Live Terminal HUD */}
              <AnimatePresence>
                {terminalOpen && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: 20 }}
                    className="absolute bottom-16 left-6 w-[33%] h-56 glass-panel overflow-hidden flex flex-col z-10"
                  >
                    <MatrixRain />
                    <div className="h-10 border-b border-white/5 bg-white/5 px-4 flex items-center gap-2 shrink-0 relative z-10">
                      <Terminal size={16} className="text-cyan-400" />
                      <span className="text-xs font-mono text-gray-400 tracking-wide">FORENSIC LOGS</span>
                      <div className="ml-auto flex gap-1">
                        <div className="w-2 h-2 rounded-full bg-red-500/60" />
                        <div className="w-2 h-2 rounded-full bg-yellow-500/60" />
                        <div className="w-2 h-2 rounded-full bg-green-500/60" />
                      </div>
                    </div>
                    <div className="flex-1 p-4 font-mono text-xs text-gray-400 space-y-1.5 overflow-y-auto">
                      <p><span className="text-green-500">[OK]</span> System boot complete — all modules loaded</p>
                      <p><span className="text-cyan-600">[SSE]</span> Connected to stream.wikimedia.org</p>
                      <p><span className="text-cyan-600">[DATA]</span> Analyzing {data.total.toLocaleString()} edits across bipartite graph</p>
                      <p><span className="text-purple-600">[DS]</span> Dempster-Shafer fusion: {data.statistics?.high_conflict_edits || 0} high-conflict edits</p>
                      <p><span className="text-yellow-600">[IF]</span> IsolationForest: anomaly detection on {data.total.toLocaleString()} vectors</p>
                      <p><span className="text-blue-600">[REP]</span> Beta-Bayesian reputation: tracking {data.top_threats?.length || 0} unique entities</p>
                      <p><span className="text-cyan-600">[STAT]</span> Avg uncertainty: {data.statistics?.avg_uncertainty?.toFixed(4) || 'N/A'}</p>
                      <p><span className="text-cyan-600">[STAT]</span> Deng entropy: {data.statistics?.avg_deng_entropy?.toFixed(4) || 'N/A'}</p>
                      <p><span className="text-red-500">[ALERT]</span> {data.distribution?.['BLOCK'] || 0} BLOCK verdicts | {data.distribution?.['FLAG'] || 0} FLAG verdicts</p>
                      <p><span className="text-green-500">[OK]</span> Intelligence pipeline: nominal <span className="cursor-blink" /></p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
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
            {threatPanelOpen && (
              <section className="flex-[2] flex flex-col p-6 bg-[#0c0c10] overflow-hidden">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-lg font-bold flex items-center gap-2">
                    Threat Matrix
                    <span className="text-xs bg-white/10 px-2 py-0.5 rounded-md text-gray-400 flex items-center gap-1.5">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                      LIVE
                    </span>
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
                      onContextMenu={(e, threat) => setContextMenu({ open: true, x: e.clientX, y: e.clientY, threat })}
                      selectedUser={selectedThreat?.user}
                      selectedTitle={selectedThreat?.title}
                      bookmarks={bookmarks}
                    />
                  )}
                </div>
              </section>
            )}
            </div>
            {/* Activity Ticker */}
            <ActivityTicker threats={data.top_threats || []} />
          </motion.div>
        ) : activePage === 'an' ? (
          /* ── Analytics ── */
          <motion.div key="an" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }} className="flex-1 overflow-y-auto">
            <AnalyticsView data={data} />
          </motion.div>
        ) : activePage === 'dt' ? (
          /* ── Data Table ── */
          <motion.div key="dt" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }} className="flex-1 overflow-hidden flex flex-col">
            <div className="px-6 py-3 border-b border-white/5 shrink-0">
              <h2 className="text-lg font-bold text-white flex items-center gap-3">
                <Table2 size={20} className="text-cyan-400" /> Intelligence Data Table
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {data.top_threats?.length || 0} threats — sortable, filterable, exportable
              </p>
            </div>
            <DataTable
              threats={data.top_threats || []}
              onSelect={(t) => setSelectedThreat(t)}
              onExport={exportData}
            />
          </motion.div>
        ) : activePage === 'ng' ? (
          /* ── Network Graph ── */
          <motion.div key="ng" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }} className="flex-1 overflow-hidden relative">
            <NetworkGraph
              threats={data.top_threats || []}
              onNodeClick={(user, title) => {
                const found = data.top_threats.find((t: any) => t.user === user && t.title === title);
                if (found) setSelectedThreat(found);
              }}
            />
          </motion.div>
        ) : activePage === 'tl' ? (
          /* ── Timeline ── */
          <motion.div key="tl" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }} className="flex-1 overflow-hidden flex flex-col">
            <div className="px-8 py-4 border-b border-white/5 shrink-0">
              <h2 className="text-lg font-bold text-white flex items-center gap-3">
                <Timer size={20} className="text-cyan-400" /> Threat Timeline
              </h2>
              <p className="text-xs text-gray-500 mt-1">
                Temporal distribution of {data.top_threats?.length || 0} analyzed edits — stacked by action verdict
              </p>
            </div>
            <div className="flex-1 min-h-0">
              <ThreatTimeline
                threats={data.top_threats || []}
                onSelect={(t) => setSelectedThreat(t)}
              />
            </div>
          </motion.div>
        ) : (
          /* ── Forensic Lab: Intelligence Report ── */
          <motion.div key="fl" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.15 }} className="flex-1 overflow-y-auto p-8">
            <div className="max-w-4xl mx-auto">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-cyan-400 flex items-center gap-3">
                  <Microscope size={22} /> Forensic Intelligence Report
                </h2>
                <div className="flex gap-2">
                  <button
                    onClick={() => { setReport(null); fetchReport(); }}
                    className="px-4 py-2 text-xs font-bold rounded-lg bg-cyan-500/20 text-cyan-400 border border-cyan-500/40 hover:bg-cyan-500/30 transition-all flex items-center gap-2"
                  >
                    <RefreshCw size={14} /> Reload Report
                  </button>
                  {report && (
                    <button
                      onClick={() => {
                        const blob = new Blob([report], { type: 'text/markdown' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = `forensic_report_${new Date().toISOString().slice(0, 10)}.md`;
                        a.click();
                        URL.revokeObjectURL(url);
                        addToast('Report exported as Markdown', 'success');
                      }}
                      className="px-4 py-2 text-xs font-bold rounded-lg bg-white/5 text-gray-400 border border-white/10 hover:bg-white/10 transition-all flex items-center gap-2"
                    >
                      <Download size={14} /> Export .md
                    </button>
                  )}
                </div>
              </div>

              {/* Methodology Summary - from actual data */}
              {data.methodology && (
                <div className="rounded-xl bg-white/[0.03] border border-white/10 p-5 mb-6">
                  <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-3">Pipeline Methodology</div>
                  <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                    {Object.entries(data.methodology as Record<string, string>).map(([key, value], i) => (
                      <motion.div
                        key={key}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: i * 0.05 }}
                        className="p-3 rounded-lg bg-white/[0.03] border border-white/5"
                      >
                        <div className="text-[9px] text-gray-600 font-bold uppercase tracking-widest mb-1">
                          {key.replace(/_/g, ' ')}
                        </div>
                        <div className="text-[11px] font-mono text-cyan-400 leading-tight">{value}</div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}

              {/* Quick Stats Row */}
              <div className="grid grid-cols-3 gap-4 mb-6">
                {[
                  { label: 'Fusion Method', value: data.methodology?.fusion?.split(' ')[0] || 'Dempster-Shafer', color: 'text-green-400' },
                  { label: 'Anomaly Detection', value: 'Isolation Forest', color: 'text-yellow-400' },
                  { label: 'Reputation Model', value: 'Beta-Bayesian', color: 'text-blue-400' },
                ].map((m, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="p-4 rounded-xl bg-white/5 border border-white/10 gradient-border"
                  >
                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-1">{m.label}</div>
                    <div className={`font-mono font-bold text-sm ${m.color}`}>{m.value}</div>
                  </motion.div>
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
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.05 }}
                    className="p-4 rounded-xl bg-white/5 border border-white/10 text-center"
                  >
                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-1">{s.label}</div>
                    <div className={`font-mono font-bold text-2xl ${s.color}`}>
                      <AnimatedNumber value={s.value as number} />
                    </div>
                  </motion.div>
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
                  <div className="text-gray-500 text-sm flex items-center gap-2">
                    <RefreshCw size={14} className="animate-spin" /> Loading report...
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
        </AnimatePresence>

        {/* Case Analysis — Slide-over panel */}
        <AnimatePresence>
          {detail && selectedThreat && (
            <>
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                onClick={() => setDetail(null)}
                className="absolute inset-0 z-[80] bg-black/40 backdrop-blur-sm"
                style={{ top: '5rem' }}
              />
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
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-gray-500 font-mono">ESC to close</span>
                    <button onClick={() => setDetail(null)} className="p-1.5 hover:bg-white/10 rounded-lg transition-colors">
                      <X size={16} />
                    </button>
                  </div>
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
                      {selectedThreat.timestamp && (
                        <span className="text-[10px] text-gray-600 font-mono">
                          {new Date(Number(selectedThreat.timestamp) * 1000).toLocaleString()}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* AI Justification */}
                  <div className="p-3 rounded-xl bg-purple-500/10 border border-purple-500/20 text-xs leading-relaxed text-purple-200 flex gap-3">
                    <Brain className="shrink-0 mt-0.5" size={16} />
                    <span>{getJustification(selectedThreat)}</span>
                  </div>

                  {/* Signal Radar + Signals Grid side by side */}
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-2">Signal Radar</div>
                      <div className="rounded-xl bg-white/[0.03] border border-white/10 p-2">
                        <SignalRadar signals={selectedThreat.signals} />
                      </div>
                    </div>
                    <div>
                      <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-2">Forensic Signals</div>
                      <div className="grid grid-cols-2 gap-2">
                        {[
                          { label: 'RULE', value: formatSignal(selectedThreat.signals.rule, ''), color: 'text-cyan-400' },
                          { label: 'NLP', value: formatSignal(selectedThreat.signals.nlp, ''), color: 'text-orange-400' },
                          { label: 'LLM', value: selectedThreat.signals.llm || 'N/A', color: 'text-purple-400' },
                          { label: 'LLM CONF', value: formatSignal(selectedThreat.signals.llm_conf), color: 'text-purple-300' },
                          { label: 'ANOMALY', value: formatSignal(selectedThreat.signals.anomaly), color: 'text-yellow-400' },
                          { label: 'REPUTATION', value: formatSignal(selectedThreat.signals.reputation), color: 'text-blue-400' },
                        ].map((s, i) => (
                          <div key={i} className="p-2.5 rounded-lg bg-white/5 border border-white/10 text-center">
                            <div className="text-[9px] text-gray-500 mb-0.5">{s.label}</div>
                            <div className={`font-mono font-bold text-sm ${s.color}`}>{s.value}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* DS Evidence */}
                  <div>
                    <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-2">Dempster-Shafer Evidence</div>
                    <div className="grid grid-cols-3 gap-2">
                      {[
                        { label: 'BELIEF', value: `${(selectedThreat.ds_belief * 100).toFixed(1)}%`, color: 'text-green-400', bar: selectedThreat.ds_belief },
                        { label: 'PLAUSIBILITY', value: `${(selectedThreat.ds_plausibility * 100).toFixed(1)}%`, color: 'text-yellow-400', bar: selectedThreat.ds_plausibility },
                        { label: 'CONFLICT (k)', value: `${(selectedThreat.ds_conflict * 100).toFixed(1)}%`, color: 'text-red-400', bar: selectedThreat.ds_conflict },
                      ].map((s, i) => (
                        <div key={i} className="p-2.5 rounded-lg bg-white/5 border border-white/10 text-center">
                          <div className="text-[10px] text-gray-500 mb-0.5">{s.label}</div>
                          <div className={`font-mono font-bold text-sm ${s.color} mb-1`}>{s.value}</div>
                          <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                            <motion.div
                              initial={{ width: 0 }}
                              animate={{ width: `${Math.min(s.bar * 100, 100)}%` }}
                              className="h-full rounded-full"
                              style={{ backgroundColor: i === 0 ? '#22c55e' : i === 1 ? '#facc15' : '#ef4444' }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Evidence Flow Diagram */}
                  {selectedThreat.mass_sources && (
                    <EvidenceFlow threat={selectedThreat} />
                  )}

                  {/* Pignistic Probability + Mass Sources (if available) */}
                  {selectedThreat.pignistic && (
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-2">Pignistic Transform</div>
                        <div className="rounded-xl bg-white/[0.03] border border-white/10 p-3 flex justify-center">
                          <PignisticGauge
                            vandalism={selectedThreat.pignistic.vandalism}
                            safe={selectedThreat.pignistic.safe}
                          />
                        </div>
                      </div>
                      {selectedThreat.mass_sources && (
                        <div>
                          <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-2">Evidence Mass Functions</div>
                          <div className="rounded-xl bg-white/[0.03] border border-white/10 p-3">
                            <MassSourceChart
                              massSources={selectedThreat.mass_sources}
                              massCombined={selectedThreat.mass_combined || { v: 0, s: 0, t: 1 }}
                            />
                          </div>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Reliability + Entropy (if available) */}
                  {selectedThreat.reliability && (
                    <div>
                      <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-2">Source Reliability & Entropy</div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="rounded-xl bg-white/[0.03] border border-white/10 p-3">
                          <div className="text-[9px] text-gray-500 font-bold mb-2">RELIABILITY WEIGHTS</div>
                          <div className="space-y-1.5">
                            {Object.entries(selectedThreat.reliability as Record<string, number>).map(([src, val]) => (
                              <div key={src} className="flex items-center gap-2">
                                <span className="text-[10px] text-gray-400 font-mono w-16 uppercase">{src}</span>
                                <div className="flex-1 h-1.5 bg-white/5 rounded-full overflow-hidden">
                                  <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${(val as number) * 100}%` }}
                                    className="h-full bg-cyan-500 rounded-full"
                                  />
                                </div>
                                <span className="text-[10px] text-gray-500 font-mono w-10 text-right">{((val as number) * 100).toFixed(0)}%</span>
                              </div>
                            ))}
                          </div>
                        </div>
                        <div className="rounded-xl bg-white/[0.03] border border-white/10 p-3">
                          <div className="text-[9px] text-gray-500 font-bold mb-2">INFORMATION THEORY</div>
                          <div className="grid grid-cols-2 gap-2">
                            {[
                              { label: 'Shannon', value: selectedThreat.entropy, color: 'text-cyan-400' },
                              { label: 'Deng', value: selectedThreat.deng_entropy, color: 'text-purple-400' },
                              { label: 'Renyi-0.5', value: selectedThreat.renyi_05, color: 'text-blue-400' },
                              { label: 'KL-Div', value: selectedThreat.kl_divergence, color: 'text-yellow-400' },
                            ].map((e, i) => (
                              <div key={i} className="text-center">
                                <div className="text-[9px] text-gray-600">{e.label}</div>
                                <div className={`font-mono text-xs font-bold ${e.color}`}>
                                  {e.value != null ? Number(e.value).toFixed(2) : 'N/A'}
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Edit Metadata */}
                  {detail.comment && (
                    <div>
                      <div className="text-[10px] text-gray-500 font-bold uppercase tracking-widest mb-2">Edit Comment</div>
                      <div className="p-3 rounded-xl bg-white/[0.03] border border-white/10 text-xs text-gray-400 italic font-mono">
                        "{detail.comment}"
                      </div>
                    </div>
                  )}

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

                  {/* Diff Viewer */}
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
                  <button className="flex-1 bg-red-500 hover:bg-red-600 text-white font-bold py-2.5 rounded-xl transition-all text-sm shadow-[0_0_15px_rgba(239,68,68,0.2)]">
                    BLOCK USER
                  </button>
                  <button
                    onClick={() => {
                      const evidence = `WIKI-STREAM EVIDENCE — ${selectedThreat.title}\nUser: ${selectedThreat.user}\nAction: ${selectedThreat.action} (${selectedThreat.score.toFixed(1)}%)\nDS Belief: ${(selectedThreat.ds_belief * 100).toFixed(1)}%\nLLM: ${selectedThreat.signals.llm || 'N/A'}\nAnomaly: ${selectedThreat.signals.anomaly}%\nReputation: ${selectedThreat.signals.reputation}%`;
                      navigator.clipboard.writeText(evidence);
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                      addToast('Evidence copied to clipboard', 'success');
                    }}
                    className="px-4 py-2.5 bg-white/5 hover:bg-white/10 rounded-xl transition-all flex items-center gap-2 text-xs text-gray-400"
                  >
                    {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
                    {copied ? 'Copied!' : 'Copy Evidence'}
                  </button>
                  <a
                    href={detail.wiki_url || `https://en.wikipedia.org/wiki/${encodeURIComponent(selectedThreat.title)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-4 py-2.5 bg-white/5 hover:bg-white/10 rounded-xl transition-all flex items-center gap-2 text-xs text-gray-400"
                  >
                    <ExternalLink size={14} /> Wikipedia
                  </a>
                </div>
              </motion.div>
            </>
          )}
        </AnimatePresence>

        {/* Status Bar */}
        <StatusBar
          connected={!!data}
          lastUpdate={data?.timestamp || null}
          total={data?.total || 0}
          distribution={data?.distribution || {}}
          pipelineRunning={pipelineRunning}
        />
      </main>
    </div>
  );
}
