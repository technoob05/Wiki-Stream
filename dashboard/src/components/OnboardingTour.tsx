import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, ChevronLeft, X, Sparkles, Globe, BarChart3, Table2, GitBranch, Microscope, Command } from 'lucide-react';

interface TourStep {
  title: string;
  description: string;
  icon: any;
  color: string;
}

const STEPS: TourStep[] = [
  { title: 'Welcome to Wiki-Stream', description: 'Real-time Wikipedia vandalism detection powered by AI. This dashboard monitors edits across multiple language domains using 7-stage intelligence pipeline.', icon: Sparkles, color: '#06b6d4' },
  { title: '3D Threat Globe', description: 'Visualize threats on a real NASA Earth map. Red markers = blocked edits, orange = flagged, yellow = under review. Drag to rotate, scroll to zoom.', icon: Globe, color: '#22c55e' },
  { title: 'Analytics Dashboard', description: 'Charts for threat distribution, score histograms, signal radar, fusion methods, and top flagged users. All data from Dempster-Shafer evidence fusion.', icon: BarChart3, color: '#a855f7' },
  { title: 'Data Table', description: 'Full sortable/filterable table with all threats. Toggle columns, export CSV, filter by action or domain. Click any row for detailed analysis.', icon: Table2, color: '#f97316' },
  { title: 'Network Graph', description: 'Force-directed graph showing user-article relationships. See which users edit which articles and how they connect.', icon: GitBranch, color: '#3b82f6' },
  { title: 'Forensic Lab', description: 'Full intelligence report with methodology details. Evidence flow diagrams, Dempster-Shafer analysis, and exportable reports.', icon: Microscope, color: '#ef4444' },
  { title: 'Pro Tips', description: 'Press Ctrl+K for command palette. Use keys 1-6 to switch pages. Press T for terminal, P to run pipeline, F for fullscreen. Right-click threats for options.', icon: Command, color: '#facc15' },
];

const STORAGE_KEY = 'wikistream_tour_done';

export const OnboardingTour: React.FC = () => {
  const [step, setStep] = useState(0);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const done = localStorage.getItem(STORAGE_KEY);
    if (!done) setVisible(true);
  }, []);

  const finish = () => {
    setVisible(false);
    localStorage.setItem(STORAGE_KEY, '1');
  };

  if (!visible) return null;

  const current = STEPS[step];

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[700] bg-black/70 backdrop-blur-sm flex items-center justify-center"
      >
        <motion.div
          key={step}
          initial={{ opacity: 0, scale: 0.9, y: 20 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.9 }}
          className="w-[480px] bg-[#0f0f13] border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
        >
          {/* Hero area */}
          <div className="h-40 flex items-center justify-center relative overflow-hidden" style={{ background: `linear-gradient(135deg, ${current.color}15, transparent)` }}>
            <div className="absolute inset-0 grid-bg opacity-50" />
            <current.icon size={56} style={{ color: current.color }} />
            {/* Step dots */}
            <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex gap-1.5">
              {STEPS.map((_, i) => (
                <div
                  key={i}
                  className={`w-1.5 h-1.5 rounded-full transition-all ${
                    i === step ? 'bg-white w-4' : i < step ? 'bg-white/40' : 'bg-white/15'
                  }`}
                />
              ))}
            </div>
          </div>

          {/* Content */}
          <div className="px-6 py-5">
            <h3 className="text-lg font-bold text-white mb-2">{current.title}</h3>
            <p className="text-sm text-gray-400 leading-relaxed">{current.description}</p>
          </div>

          {/* Actions */}
          <div className="px-6 py-4 border-t border-white/5 flex items-center justify-between">
            <button onClick={finish} className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
              Skip tour
            </button>
            <div className="flex gap-2">
              {step > 0 && (
                <button
                  onClick={() => setStep(s => s - 1)}
                  className="px-3 py-1.5 text-xs bg-white/5 hover:bg-white/10 rounded-lg text-gray-400 flex items-center gap-1 transition-colors"
                >
                  <ChevronLeft size={12} /> Back
                </button>
              )}
              {step < STEPS.length - 1 ? (
                <button
                  onClick={() => setStep(s => s + 1)}
                  className="px-4 py-1.5 text-xs bg-cyan-500 hover:bg-cyan-600 rounded-lg text-black font-bold flex items-center gap-1 transition-colors"
                >
                  Next <ChevronRight size={12} />
                </button>
              ) : (
                <button
                  onClick={finish}
                  className="px-4 py-1.5 text-xs bg-cyan-500 hover:bg-cyan-600 rounded-lg text-black font-bold flex items-center gap-1 transition-colors"
                >
                  Get Started <Sparkles size={12} />
                </button>
              )}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};
