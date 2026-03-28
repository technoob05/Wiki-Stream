import { motion } from 'framer-motion';
import {
  Database, Cpu, Shield, Brain, Fingerprint, Layers, FileText, CheckCircle, Loader,
} from 'lucide-react';

interface PipelineProgressProps {
  running: boolean;
  currentStage?: number;
}

const stages = [
  { id: 1, name: 'Data Collection', desc: 'Streaming from Wikimedia SSE', icon: Database },
  { id: 2, name: 'Feature Extraction', desc: 'Multi-scale information theory', icon: Cpu },
  { id: 3, name: 'Ground Truth', desc: 'Wikipedia revert validation', icon: Shield },
  { id: 4, name: 'LLM Classification', desc: 'Gemma 2 via Ollama', icon: Brain },
  { id: 5, name: 'User Attribution', desc: 'Stylometric fingerprinting', icon: Fingerprint },
  { id: 6, name: 'Intelligence Fusion', desc: 'Dempster-Shafer + Graph ranking', icon: Layers },
  { id: 7, name: 'Report Generation', desc: 'Forensic report synthesis', icon: FileText },
];

export const PipelineProgress: React.FC<PipelineProgressProps> = ({ running, currentStage = 0 }) => {
  // Simulate progress when running
  const simulatedStage = running ? Math.min(Math.floor(Date.now() / 8000) % 8, 7) : 0;
  const active = running ? Math.max(currentStage, simulatedStage) : 0;

  if (!running) return null;

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="border-b border-white/5 bg-[#0a0a0c]/80 backdrop-blur-md overflow-hidden"
    >
      <div className="px-8 py-4">
        <div className="flex items-center gap-3 mb-3">
          <Loader size={14} className="text-cyan-400 animate-spin" />
          <span className="text-xs font-bold text-cyan-400 uppercase tracking-widest">Pipeline Running</span>
          <span className="text-[10px] text-gray-600 font-mono">Stage {active + 1}/7</span>
        </div>

        <div className="flex gap-1">
          {stages.map((stage, i) => {
            const isDone = i < active;
            const isCurrent = i === active;
            const _isPending = i > active; void _isPending;

            return (
              <div key={stage.id} className="flex-1 flex flex-col items-center gap-1.5">
                {/* Progress bar segment */}
                <div className="w-full h-1 rounded-full overflow-hidden bg-white/5">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width: isDone ? '100%' : isCurrent ? '60%' : '0%',
                    }}
                    transition={{ duration: 0.5 }}
                    className={`h-full rounded-full ${
                      isDone ? 'bg-green-500' : isCurrent ? 'bg-cyan-500' : 'bg-white/5'
                    }`}
                  />
                </div>

                {/* Icon */}
                <div className={`p-1.5 rounded-lg transition-all ${
                  isDone ? 'bg-green-500/15 text-green-400' :
                  isCurrent ? 'bg-cyan-500/15 text-cyan-400' :
                  'bg-white/5 text-gray-600'
                }`}>
                  {isDone ? (
                    <CheckCircle size={12} />
                  ) : isCurrent ? (
                    <stage.icon size={12} className="animate-pulse" />
                  ) : (
                    <stage.icon size={12} />
                  )}
                </div>

                {/* Label */}
                <div className="text-center">
                  <div className={`text-[9px] font-bold ${
                    isDone ? 'text-green-400' : isCurrent ? 'text-cyan-400' : 'text-gray-600'
                  }`}>
                    {stage.name}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
};
