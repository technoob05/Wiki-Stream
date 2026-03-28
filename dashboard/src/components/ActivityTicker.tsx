import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Zap } from 'lucide-react';

interface Props {
  threats: any[];
}

const actionColor: Record<string, string> = {
  BLOCK: 'text-red-400',
  FLAG: 'text-orange-400',
  REVIEW: 'text-yellow-400',
  SAFE: 'text-green-400',
};

export const ActivityTicker: React.FC<Props> = ({ threats }) => {
  const [current, setCurrent] = useState(0);
  const _idRef = useRef(0); void _idRef;

  useEffect(() => {
    if (!threats.length) return;
    const interval = setInterval(() => {
      setCurrent(c => (c + 1) % threats.length);
    }, 3000);
    return () => clearInterval(interval);
  }, [threats.length]);

  if (!threats.length) return null;

  const t = threats[current];
  if (!t) return null;

  return (
    <div className="h-8 bg-black/40 backdrop-blur-sm border-t border-white/5 flex items-center px-4 gap-3 overflow-hidden">
      <div className="flex items-center gap-1.5 shrink-0">
        <Zap size={10} className="text-cyan-500" />
        <span className="text-[10px] font-bold text-cyan-500 uppercase tracking-widest">LIVE FEED</span>
      </div>
      <div className="w-px h-3 bg-white/10 shrink-0" />
      <div className="flex-1 overflow-hidden relative h-full flex items-center">
        <AnimatePresence mode="wait">
          <motion.div
            key={`${current}-${t.user}`}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.3 }}
            className="flex items-center gap-3 text-[11px] font-mono whitespace-nowrap"
          >
            <span className={`font-bold ${actionColor[t.action] || 'text-gray-400'}`}>
              [{t.action}]
            </span>
            <span className="text-blue-400">{t.user}</span>
            <span className="text-gray-600">edited</span>
            <span className="text-white font-medium">{t.title?.slice(0, 50)}{(t.title?.length || 0) > 50 ? '...' : ''}</span>
            <span className="text-gray-600">—</span>
            <span className="text-gray-400">score: {t.score?.toFixed(1)}%</span>
            {t.domain && <span className="text-gray-600 text-[10px]">({t.domain})</span>}
          </motion.div>
        </AnimatePresence>
      </div>
      <div className="shrink-0 text-[10px] text-gray-600 font-mono">
        {current + 1}/{threats.length}
      </div>
    </div>
  );
};
