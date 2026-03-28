import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bell, X, Trash2, AlertTriangle, Zap, Activity, CheckCircle } from 'lucide-react';

export interface AppNotification {
  id: number;
  message: string;
  type: 'threat' | 'info' | 'success';
  time: Date;
  read: boolean;
}

interface NotificationCenterProps {
  notifications: AppNotification[];
  onClear: () => void;
  onMarkRead: (id: number) => void;
}

export const NotificationCenter: React.FC<NotificationCenterProps> = ({ notifications, onClear, onMarkRead }) => {
  const [open, setOpen] = useState(false);
  const unread = notifications.filter(n => !n.read).length;

  const icon = (type: string) => {
    if (type === 'threat') return <AlertTriangle size={12} className="text-red-400 shrink-0" />;
    if (type === 'success') return <CheckCircle size={12} className="text-green-400 shrink-0" />;
    return <Activity size={12} className="text-cyan-400 shrink-0" />;
  };

  const timeAgo = (date: Date) => {
    const s = Math.floor((Date.now() - date.getTime()) / 1000);
    if (s < 60) return `${s}s ago`;
    if (s < 3600) return `${Math.floor(s / 60)}m ago`;
    return `${Math.floor(s / 3600)}h ago`;
  };

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="relative p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/5 transition-all"
        title="Notifications"
      >
        <Bell size={14} className="text-gray-400" />
        {unread > 0 && (
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-[9px] font-bold text-white flex items-center justify-center animate-pulse">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      <AnimatePresence>
        {open && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOpen(false)}
              className="fixed inset-0 z-[100]"
            />
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.95 }}
              className="absolute right-0 top-full mt-2 w-[360px] bg-[#0f0f13] border border-white/10 rounded-xl shadow-2xl z-[101] overflow-hidden"
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-white/5">
                <div className="flex items-center gap-2">
                  <Bell size={14} className="text-cyan-400" />
                  <span className="text-xs font-bold text-white">Notifications</span>
                  {unread > 0 && <span className="text-[10px] bg-red-500/20 text-red-400 px-1.5 py-0.5 rounded-full font-bold">{unread}</span>}
                </div>
                <div className="flex gap-1">
                  {notifications.length > 0 && (
                    <button onClick={onClear} className="p-1 hover:bg-white/10 rounded text-gray-500 hover:text-gray-300" title="Clear all">
                      <Trash2 size={12} />
                    </button>
                  )}
                  <button onClick={() => setOpen(false)} className="p-1 hover:bg-white/10 rounded text-gray-500 hover:text-gray-300">
                    <X size={12} />
                  </button>
                </div>
              </div>

              <div className="max-h-[320px] overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="px-4 py-8 text-center text-gray-600 text-xs">No notifications yet</div>
                ) : (
                  notifications.slice().reverse().map(n => (
                    <div
                      key={n.id}
                      onClick={() => onMarkRead(n.id)}
                      className={`px-4 py-3 border-b border-white/[0.03] flex items-start gap-3 cursor-pointer transition-colors hover:bg-white/[0.03] ${
                        !n.read ? 'bg-white/[0.02]' : ''
                      }`}
                    >
                      <div className="mt-0.5">{icon(n.type)}</div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-xs ${!n.read ? 'text-white' : 'text-gray-400'}`}>{n.message}</p>
                        <p className="text-[10px] text-gray-600 mt-0.5">{timeAgo(n.time)}</p>
                      </div>
                      {!n.read && <div className="w-1.5 h-1.5 rounded-full bg-cyan-500 mt-1.5 shrink-0" />}
                    </div>
                  ))
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
};
