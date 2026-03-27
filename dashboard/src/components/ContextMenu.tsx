import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Copy, ExternalLink, Shield, Bookmark, BookmarkCheck, Eye, Download } from 'lucide-react';

interface ContextMenuItem {
  label: string;
  icon: any;
  action: () => void;
  danger?: boolean;
  separator?: boolean;
}

interface ContextMenuProps {
  x: number;
  y: number;
  open: boolean;
  onClose: () => void;
  items: ContextMenuItem[];
}

export const ContextMenu: React.FC<ContextMenuProps> = ({ x, y, open, onClose, items }) => {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    };
    const keyHandler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    window.addEventListener('mousedown', handler);
    window.addEventListener('keydown', keyHandler);
    return () => { window.removeEventListener('mousedown', handler); window.removeEventListener('keydown', keyHandler); };
  }, [open, onClose]);

  // Clamp to viewport
  const adjustedX = Math.min(x, window.innerWidth - 200);
  const adjustedY = Math.min(y, window.innerHeight - items.length * 36 - 20);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          ref={ref}
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          transition={{ duration: 0.1 }}
          className="fixed z-[600] bg-[#0f0f13] border border-white/10 rounded-xl shadow-2xl py-1.5 min-w-[180px]"
          style={{ left: adjustedX, top: adjustedY }}
        >
          {items.map((item, i) => (
            <div key={i}>
              {item.separator && i > 0 && <div className="my-1 border-t border-white/5" />}
              <button
                onClick={() => { item.action(); onClose(); }}
                className={`w-full flex items-center gap-2.5 px-3 py-2 text-xs transition-colors ${
                  item.danger
                    ? 'text-red-400 hover:bg-red-500/10'
                    : 'text-gray-400 hover:bg-white/5 hover:text-white'
                }`}
              >
                <item.icon size={13} />
                {item.label}
              </button>
            </div>
          ))}
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export type { ContextMenuItem };
