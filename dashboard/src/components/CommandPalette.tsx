import { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, Activity, BarChart3, Microscope, Terminal, RefreshCw,
  Download, Keyboard, Shield, Globe, ArrowRight, Command,
} from 'lucide-react';

interface Action {
  id: string;
  label: string;
  description: string;
  icon: any;
  category: string;
  shortcut?: string;
  action: () => void;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  actions: Action[];
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({ open, onClose, actions }) => {
  const [query, setQuery] = useState('');
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = useMemo(() => {
    if (!query.trim()) return actions;
    const q = query.toLowerCase();
    return actions.filter(a =>
      a.label.toLowerCase().includes(q) ||
      a.description.toLowerCase().includes(q) ||
      a.category.toLowerCase().includes(q)
    );
  }, [query, actions]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIdx(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    setSelectedIdx(0);
  }, [query]);

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIdx(i => Math.min(i + 1, filtered.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIdx(i => Math.max(i - 1, 0));
      } else if (e.key === 'Enter' && filtered[selectedIdx]) {
        e.preventDefault();
        filtered[selectedIdx].action();
        onClose();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, filtered, selectedIdx, onClose]);

  // Group by category
  const grouped = useMemo(() => {
    const groups: Record<string, typeof filtered> = {};
    filtered.forEach(a => {
      if (!groups[a.category]) groups[a.category] = [];
      groups[a.category].push(a);
    });
    return groups;
  }, [filtered]);

  let globalIdx = -1;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-[400] bg-black/60 backdrop-blur-sm flex items-start justify-center pt-[15vh]"
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0, y: -10 }}
            animate={{ scale: 1, opacity: 1, y: 0 }}
            exit={{ scale: 0.95, opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            onClick={e => e.stopPropagation()}
            className="w-[560px] bg-[#0f0f13] border border-white/10 rounded-2xl shadow-2xl overflow-hidden"
          >
            {/* Search Input */}
            <div className="flex items-center gap-3 px-4 py-3 border-b border-white/5">
              <Search size={16} className="text-gray-500 shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search commands..."
                className="flex-1 bg-transparent text-sm text-white placeholder:text-gray-600 focus:outline-none"
              />
              <kbd className="px-1.5 py-0.5 bg-white/5 border border-white/10 rounded text-[10px] font-mono text-gray-500">ESC</kbd>
            </div>

            {/* Results */}
            <div className="max-h-[350px] overflow-y-auto py-2">
              {filtered.length === 0 ? (
                <div className="px-4 py-8 text-center text-gray-600 text-xs">
                  No commands found for "{query}"
                </div>
              ) : (
                Object.entries(grouped).map(([category, items]) => (
                  <div key={category}>
                    <div className="px-4 py-1.5 text-[9px] text-gray-600 font-bold uppercase tracking-widest">
                      {category}
                    </div>
                    {items.map((item) => {
                      globalIdx++;
                      const idx = globalIdx;
                      const isSelected = idx === selectedIdx;
                      return (
                        <button
                          key={item.id}
                          onClick={() => { item.action(); onClose(); }}
                          onMouseEnter={() => setSelectedIdx(idx)}
                          className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                            isSelected ? 'bg-cyan-500/10 text-white' : 'text-gray-400 hover:bg-white/5'
                          }`}
                        >
                          <item.icon size={16} className={isSelected ? 'text-cyan-400' : 'text-gray-500'} />
                          <div className="flex-1 min-w-0">
                            <div className="text-sm font-medium truncate">{item.label}</div>
                            <div className="text-[10px] text-gray-600 truncate">{item.description}</div>
                          </div>
                          {item.shortcut && (
                            <kbd className="px-1.5 py-0.5 bg-white/5 border border-white/10 rounded text-[10px] font-mono text-gray-500 shrink-0">
                              {item.shortcut}
                            </kbd>
                          )}
                          {isSelected && <ArrowRight size={12} className="text-cyan-400 shrink-0" />}
                        </button>
                      );
                    })}
                  </div>
                ))
              )}
            </div>

            {/* Footer */}
            <div className="px-4 py-2 border-t border-white/5 flex items-center gap-4 text-[10px] text-gray-600">
              <span className="flex items-center gap-1"><Command size={10} />K to open</span>
              <span>Arrow keys to navigate</span>
              <span>Enter to select</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export type { Action };
