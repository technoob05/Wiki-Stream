import { motion } from 'framer-motion';
import { ArrowRight } from 'lucide-react';

interface EvidenceFlowProps {
  threat: any;
}

const sourceColor: Record<string, string> = {
  rule: '#06b6d4',
  nlp: '#f97316',
  llm: '#a855f7',
  attribution: '#3b82f6',
};

export const EvidenceFlow: React.FC<EvidenceFlowProps> = ({ threat }) => {
  if (!threat.mass_sources || !threat.mass_combined) return null;

  const sources = Object.entries(threat.mass_sources as Record<string, { v: number; s: number; t: number }>);
  const combined = threat.mass_combined;
  const pignistic = threat.pignistic;
  const action = threat.action;

  const actionColor: Record<string, string> = {
    BLOCK: '#ef4444', FLAG: '#f97316', REVIEW: '#facc15', SAFE: '#22c55e',
  };

  return (
    <div className="p-4 rounded-xl bg-white/[0.02] border border-white/10">
      <div className="text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-4">Evidence Fusion Pipeline</div>

      <div className="flex items-center gap-2 overflow-x-auto pb-2">
        {/* Evidence Sources */}
        <div className="flex flex-col gap-1.5 shrink-0">
          {sources.map(([name, masses], i) => {
            const maxMass = Math.max(masses.v, masses.s, masses.t);
            const dominant = masses.v === maxMass ? 'V' : masses.s === maxMass ? 'S' : 'U';
            return (
              <motion.div
                key={name}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.1 }}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-white/10"
                style={{ borderLeftColor: sourceColor[name] || '#666', borderLeftWidth: 3 }}
              >
                <span className="text-[10px] font-mono font-bold uppercase w-12" style={{ color: sourceColor[name] || '#999' }}>
                  {name}
                </span>
                <div className="flex gap-1">
                  <span className={`text-[9px] font-mono px-1 rounded ${dominant === 'V' ? 'bg-red-500/20 text-red-400' : 'text-gray-600'}`}>
                    v:{(masses.v * 100).toFixed(0)}
                  </span>
                  <span className={`text-[9px] font-mono px-1 rounded ${dominant === 'S' ? 'bg-green-500/20 text-green-400' : 'text-gray-600'}`}>
                    s:{(masses.s * 100).toFixed(0)}
                  </span>
                  <span className={`text-[9px] font-mono px-1 rounded ${dominant === 'U' ? 'bg-gray-500/20 text-gray-400' : 'text-gray-600'}`}>
                    θ:{(masses.t * 100).toFixed(0)}
                  </span>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* Arrow */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="flex flex-col items-center gap-1 shrink-0 px-2">
          <div className="text-[8px] text-gray-600 font-mono">{threat.ds_method || 'Murphy'}</div>
          <ArrowRight size={16} className="text-cyan-500" />
          <div className="text-[8px] text-gray-600 font-mono">DS Fusion</div>
        </motion.div>

        {/* Combined Mass */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.5 }}
          className="shrink-0 p-3 rounded-xl bg-cyan-500/10 border border-cyan-500/20"
        >
          <div className="text-[9px] text-cyan-400 font-bold mb-1.5">COMBINED</div>
          <div className="flex gap-2">
            <div className="text-center">
              <div className="text-[9px] text-gray-500">m(v)</div>
              <div className="text-sm font-mono font-bold text-red-400">{(combined.v * 100).toFixed(1)}%</div>
            </div>
            <div className="text-center">
              <div className="text-[9px] text-gray-500">m(s)</div>
              <div className="text-sm font-mono font-bold text-green-400">{(combined.s * 100).toFixed(1)}%</div>
            </div>
            <div className="text-center">
              <div className="text-[9px] text-gray-500">m(θ)</div>
              <div className="text-sm font-mono font-bold text-gray-400">{(combined.t * 100).toFixed(1)}%</div>
            </div>
          </div>
          <div className="text-[9px] text-gray-500 mt-1">k = {((threat.ds_conflict || 0) * 100).toFixed(1)}%</div>
        </motion.div>

        {/* Arrow */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.7 }} className="flex flex-col items-center gap-1 shrink-0 px-2">
          <div className="text-[8px] text-gray-600 font-mono">Pignistic</div>
          <ArrowRight size={16} className="text-purple-500" />
          <div className="text-[8px] text-gray-600 font-mono">BetP</div>
        </motion.div>

        {/* Pignistic */}
        {pignistic && (
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.8 }}
            className="shrink-0 p-3 rounded-xl bg-purple-500/10 border border-purple-500/20"
          >
            <div className="text-[9px] text-purple-400 font-bold mb-1.5">PIGNISTIC</div>
            <div className="flex gap-3">
              <div className="text-center">
                <div className="text-[9px] text-gray-500">P(v)</div>
                <div className="text-sm font-mono font-bold text-red-400">{(pignistic.vandalism * 100).toFixed(1)}%</div>
              </div>
              <div className="text-center">
                <div className="text-[9px] text-gray-500">P(s)</div>
                <div className="text-sm font-mono font-bold text-green-400">{(pignistic.safe * 100).toFixed(1)}%</div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Arrow */}
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.0 }} className="flex flex-col items-center gap-1 shrink-0 px-2">
          <ArrowRight size={16} className="text-gray-500" />
          <div className="text-[8px] text-gray-600 font-mono">Decision</div>
        </motion.div>

        {/* Final Verdict */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 1.1 }}
          className="shrink-0 p-3 rounded-xl border-2 text-center min-w-[80px]"
          style={{ borderColor: actionColor[action] || '#666', backgroundColor: `${actionColor[action]}15` }}
        >
          <div className="text-lg font-bold font-mono" style={{ color: actionColor[action] || '#999' }}>
            {action}
          </div>
          <div className="text-xs font-mono text-gray-400">{threat.score?.toFixed(1)}%</div>
        </motion.div>
      </div>
    </div>
  );
};
