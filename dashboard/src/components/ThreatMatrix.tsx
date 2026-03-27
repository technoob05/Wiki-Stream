import { AlertTriangle, ShieldCheck, Brain } from 'lucide-react';
import { motion } from 'framer-motion';

interface Threat {
  user: string;
  title: string;
  score: number;
  action: string;
  timestamp: string;
  ds_belief: number;
  ds_plausibility: number;
  ds_conflict: number;
  signals: {
    rule: number;
    nlp: number;
    llm: string;        // "VANDALISM" | "SUSPICIOUS" | "SAFE" | ""
    llm_conf: string;   // "0.7" or ""
    attribution: string;
    anomaly: number;
    reputation: number;
    graph: number;
  };
}

interface Props {
  threats: Threat[];
  onSelect: (threat: Threat) => void;
  selectedUser?: string;
  selectedTitle?: string;
}

export type { Threat };

export const ThreatMatrix: React.FC<Props> = ({ threats, onSelect, selectedUser, selectedTitle }) => {
  return (
    <div className="flex flex-col gap-3 overflow-y-auto pr-2">
      {threats.map((threat, idx) => {
        const isSelected = selectedUser === threat.user && selectedTitle === threat.title;
        const colorClass =
          threat.action.includes('BLOCK') ? 'text-red-500 border-red-500/30 bg-red-500/10' :
          threat.action.includes('FLAG') ? 'text-orange-500 border-orange-500/30 bg-orange-500/10' :
          threat.action.includes('REVIEW') ? 'text-yellow-500 border-yellow-500/30 bg-yellow-500/10' :
          'text-green-500 border-green-500/30 bg-green-500/10';

        // Derive reason from actual signal data
        const llmClass = threat.signals.llm || '';
        const reason = llmClass === 'VANDALISM' ? "LLM: High Vandalism Confidence" :
                       llmClass === 'SUSPICIOUS' ? "LLM: Suspicious Pattern Detected" :
                       threat.signals.rule > 3 ? "Rule Engine: Structural Anomaly" :
                       threat.signals.nlp > 5 ? "NLP: Content Anomaly Detected" :
                       threat.signals.anomaly > 80 ? "Isolation Forest: Multivariate Outlier" :
                       "Standard Verification Path";

        return (
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: idx * 0.05 }}
            key={`${threat.user}-${threat.title}-${idx}`}
            onClick={() => onSelect(threat)}
            className={`cursor-pointer p-4 rounded-xl border transition-all duration-300 glass-panel ${
              isSelected ? 'border-cyan-500/50 bg-cyan-500/10' : 'hover:border-white/20'
            }`}
          >
            <div className="flex justify-between items-start mb-2">
              <div className="flex items-center gap-2">
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${colorClass}`}>
                  {threat.action}
                </span>
                <span className="text-[10px] font-mono text-gray-500">{threat.score.toFixed(1)}%</span>
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

            <div className="flex justify-between items-center">
              <span className="text-xs text-blue-400 font-mono">{threat.user}</span>
              <div className="flex gap-1">
                {llmClass === 'VANDALISM' && <Brain size={12} className="text-purple-400" />}
                {llmClass === 'SUSPICIOUS' && <Brain size={12} className="text-purple-400 opacity-60" />}
                {threat.signals.rule > 2 && <ShieldCheck size={12} className="text-cyan-400" />}
                {threat.signals.nlp > 3 && <AlertTriangle size={12} className="text-orange-400" />}
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
};
