import { useState, useMemo } from 'react';
import { AlertTriangle, ShieldCheck, Brain, Search, ArrowUpDown, Clock, Bookmark } from 'lucide-react';
import { motion } from 'framer-motion';

interface Threat {
  user: string;
  title: string;
  score: number;
  action: string;
  timestamp: string;
  domain: string;
  ds_belief: number;
  ds_plausibility: number;
  ds_conflict: number;
  ds_uncertainty: number;
  ds_method: string;
  deng_entropy: number;
  entropy: number;
  renyi_05: number;
  renyi_2: number;
  tsallis_05: number;
  kl_divergence: number;
  comment: string;
  pignistic: { vandalism: number; safe: number };
  reliability: Record<string, number>;
  mass_combined: { v: number; s: number; t: number };
  mass_sources: Record<string, { v: number; s: number; t: number }>;
  signals: {
    rule: number;
    nlp: number;
    llm: string;
    llm_conf: string;
    attribution: string;
    anomaly: number;
    reputation: number;
    pagerank: number;
    hits_hub: number;
    hits_authority: number;
    graph: number;
  };
}

interface Props {
  threats: Threat[];
  onSelect: (threat: Threat) => void;
  onContextMenu?: (e: React.MouseEvent, threat: Threat) => void;
  selectedUser?: string;
  selectedTitle?: string;
  bookmarks?: Set<string>;
}

export type { Threat };

type SortKey = 'score' | 'time' | 'belief';

export const ThreatMatrix: React.FC<Props> = ({ threats, onSelect, onContextMenu, selectedUser, selectedTitle, bookmarks }) => {
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState<SortKey>('score');

  const filtered = useMemo(() => {
    let result = threats;
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(t =>
        t.user.toLowerCase().includes(q) ||
        t.title.toLowerCase().includes(q) ||
        t.action.toLowerCase().includes(q)
      );
    }
    return [...result].sort((a, b) => {
      if (sortBy === 'score') return b.score - a.score;
      if (sortBy === 'belief') return (b.ds_belief || 0) - (a.ds_belief || 0);
      if (sortBy === 'time') return Number(b.timestamp || 0) - Number(a.timestamp || 0);
      return 0;
    });
  }, [threats, search, sortBy]);

  return (
    <div className="flex flex-col gap-3 overflow-y-auto pr-2">
      {/* Search + Sort Bar */}
      <div className="flex gap-2 sticky top-0 z-10 pb-2">
        <div className="flex-1 relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search user or article..."
            className="w-full bg-white/5 border border-white/10 rounded-lg pl-8 pr-3 py-2 text-xs text-gray-300 placeholder:text-gray-600 focus:outline-none search-glow transition-all"
          />
        </div>
        <div className="flex gap-1">
          {([
            { key: 'score' as SortKey, icon: ArrowUpDown, label: 'Score' },
            { key: 'belief' as SortKey, icon: Brain, label: 'Belief' },
            { key: 'time' as SortKey, icon: Clock, label: 'Time' },
          ]).map(s => (
            <button
              key={s.key}
              onClick={() => setSortBy(s.key)}
              title={`Sort by ${s.label}`}
              className={`p-2 rounded-lg border text-[10px] transition-all ${
                sortBy === s.key
                  ? 'bg-cyan-500/15 border-cyan-500/30 text-cyan-400'
                  : 'bg-white/5 border-white/10 text-gray-500 hover:text-gray-300'
              }`}
            >
              <s.icon size={12} />
            </button>
          ))}
        </div>
      </div>

      {/* Results count */}
      {search && (
        <div className="text-[10px] text-gray-500 font-mono">
          {filtered.length} result{filtered.length !== 1 ? 's' : ''} for "{search}"
        </div>
      )}

      {/* Threat List */}
      {filtered.map((threat, idx) => {
        const isSelected = selectedUser === threat.user && selectedTitle === threat.title;
        const colorClass =
          threat.action.includes('BLOCK') ? 'text-red-500 border-red-500/30 bg-red-500/10' :
          threat.action.includes('FLAG') ? 'text-orange-500 border-orange-500/30 bg-orange-500/10' :
          threat.action.includes('REVIEW') ? 'text-yellow-500 border-yellow-500/30 bg-yellow-500/10' :
          'text-green-500 border-green-500/30 bg-green-500/10';

        const llmClass = threat.signals.llm || '';
        const reason = llmClass === 'VANDALISM' ? "LLM: High Vandalism Confidence" :
                       llmClass === 'SUSPICIOUS' ? "LLM: Suspicious Pattern Detected" :
                       threat.signals.rule > 3 ? "Rule Engine: Structural Anomaly" :
                       threat.signals.nlp > 5 ? "NLP: Content Anomaly Detected" :
                       threat.signals.anomaly > 80 ? "Isolation Forest: Multivariate Outlier" :
                       "Standard Verification Path";

        // Signal count for quick glance
        const activeSignals = [
          llmClass === 'VANDALISM' || llmClass === 'SUSPICIOUS',
          threat.signals.rule > 2,
          threat.signals.nlp > 3,
          threat.signals.anomaly > 50,
          threat.signals.reputation > 50,
        ].filter(Boolean).length;

        return (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: Math.min(idx * 0.03, 0.5) }}
            key={`${threat.user}-${threat.title}-${idx}`}
            onClick={() => onSelect(threat)}
            onContextMenu={(e) => { e.preventDefault(); onContextMenu?.(e, threat); }}
            className={`cursor-pointer p-4 rounded-xl border transition-all duration-300 threat-card glass-panel ${
              isSelected ? 'border-cyan-500/50 bg-cyan-500/10 shadow-[0_0_20px_rgba(6,182,212,0.1)]' : 'hover:border-white/20'
            }`}
          >
            <div className="flex justify-between items-start mb-2">
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${colorClass}`}>
                  {threat.action}
                </span>
                <span className="text-[10px] font-mono text-gray-500">{threat.score.toFixed(1)}%</span>
                {activeSignals >= 3 && (
                  <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">
                    {activeSignals} SIGNALS
                  </span>
                )}
              </div>
              {threat.timestamp && (
                <span className="text-[10px] text-gray-500 font-mono">
                  {new Date(Number(threat.timestamp) * 1000).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                </span>
              )}
            </div>

            <h4 className="text-sm font-semibold text-white mb-1 line-clamp-1">
               <span className="text-gray-500 font-normal">Article:</span> {threat.title}
            </h4>

            <p className="text-[10px] text-gray-400 mb-2 italic">
               Reason: {reason}
            </p>

            {/* Severity Bar */}
            <div className="mb-2">
              <div className="h-1 bg-white/5 rounded-full overflow-hidden">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${Math.min(threat.score, 100)}%` }}
                  transition={{ duration: 0.6, delay: Math.min(idx * 0.03, 0.5) }}
                  className="h-full rounded-full"
                  style={{
                    backgroundColor: threat.score > 70 ? '#ef4444' : threat.score > 40 ? '#f97316' : threat.score > 20 ? '#facc15' : '#22c55e',
                  }}
                />
              </div>
            </div>

            <div className="flex justify-between items-center">
              <div className="flex items-center gap-1.5">
                {bookmarks?.has(`${threat.user}::${threat.title}`) && (
                  <Bookmark size={10} className="text-cyan-400 fill-cyan-400" />
                )}
                <span className="text-xs text-blue-400 font-mono">{threat.user}</span>
              </div>
              <div className="flex gap-1.5 items-center">
                {/* DS Belief mini badge */}
                <span className="text-[9px] font-mono text-gray-500 bg-white/5 px-1.5 py-0.5 rounded">
                  DS:{(threat.ds_belief * 100).toFixed(0)}%
                </span>
                {llmClass === 'VANDALISM' && <Brain size={12} className="text-purple-400" />}
                {llmClass === 'SUSPICIOUS' && <Brain size={12} className="text-purple-400 opacity-60" />}
                {threat.signals.rule > 2 && <ShieldCheck size={12} className="text-cyan-400" />}
                {threat.signals.nlp > 3 && <AlertTriangle size={12} className="text-orange-400" />}
              </div>
            </div>
          </motion.div>
        );
      })}

      {filtered.length === 0 && search && (
        <div className="flex flex-col items-center justify-center py-12 text-gray-600 gap-2">
          <Search size={24} />
          <p className="text-xs font-mono">No matches for "{search}"</p>
        </div>
      )}
    </div>
  );
};
