import { motion, AnimatePresence } from 'framer-motion';
import { X, Palette, Volume2, VolumeX, Eye, Monitor, Sun, Moon } from 'lucide-react';

interface Settings {
  accentColor: string;
  soundEnabled: boolean;
  scanlines: boolean;
  density: 'compact' | 'normal' | 'comfortable';
  autoRefresh: boolean;
  refreshInterval: number;
}

interface SettingsPanelProps {
  open: boolean;
  onClose: () => void;
  settings: Settings;
  onChange: (settings: Settings) => void;
}

const ACCENT_COLORS = [
  { name: 'Cyan', value: '#06b6d4' },
  { name: 'Purple', value: '#a855f7' },
  { name: 'Blue', value: '#3b82f6' },
  { name: 'Green', value: '#22c55e' },
  { name: 'Rose', value: '#f43f5e' },
  { name: 'Amber', value: '#f59e0b' },
];

export const SettingsPanel: React.FC<SettingsPanelProps> = ({ open, onClose, settings, onChange }) => {
  const update = (partial: Partial<Settings>) => onChange({ ...settings, ...partial });

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="fixed inset-0 z-[300] bg-black/60 backdrop-blur-sm flex items-center justify-center"
        >
          <motion.div
            initial={{ scale: 0.95, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.95, opacity: 0 }}
            onClick={e => e.stopPropagation()}
            className="bg-[#0f0f13] border border-white/10 rounded-2xl p-6 w-[460px] shadow-2xl"
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                <Monitor size={16} className="text-cyan-400" /> Settings
              </h3>
              <button onClick={onClose} className="p-1 hover:bg-white/10 rounded-lg">
                <X size={14} className="text-gray-400" />
              </button>
            </div>

            <div className="space-y-5">
              {/* Accent Color */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Palette size={14} className="text-gray-400" />
                  <span className="text-xs font-bold text-gray-300">Accent Color</span>
                </div>
                <div className="flex gap-2">
                  {ACCENT_COLORS.map(c => (
                    <button
                      key={c.value}
                      onClick={() => update({ accentColor: c.value })}
                      className={`w-8 h-8 rounded-lg border-2 transition-all ${
                        settings.accentColor === c.value
                          ? 'border-white scale-110 shadow-lg'
                          : 'border-transparent hover:border-white/30'
                      }`}
                      style={{ backgroundColor: c.value }}
                      title={c.name}
                    />
                  ))}
                </div>
              </div>

              {/* Sound */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {settings.soundEnabled ? <Volume2 size={14} className="text-gray-400" /> : <VolumeX size={14} className="text-gray-400" />}
                  <span className="text-xs font-bold text-gray-300">Alert Sounds</span>
                </div>
                <button
                  onClick={() => update({ soundEnabled: !settings.soundEnabled })}
                  className={`w-10 h-5 rounded-full transition-all ${settings.soundEnabled ? 'bg-cyan-500' : 'bg-white/10'}`}
                >
                  <motion.div
                    animate={{ x: settings.soundEnabled ? 20 : 2 }}
                    className="w-4 h-4 rounded-full bg-white shadow"
                  />
                </button>
              </div>

              {/* Scanlines */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Eye size={14} className="text-gray-400" />
                  <span className="text-xs font-bold text-gray-300">CRT Scanlines</span>
                </div>
                <button
                  onClick={() => update({ scanlines: !settings.scanlines })}
                  className={`w-10 h-5 rounded-full transition-all ${settings.scanlines ? 'bg-cyan-500' : 'bg-white/10'}`}
                >
                  <motion.div
                    animate={{ x: settings.scanlines ? 20 : 2 }}
                    className="w-4 h-4 rounded-full bg-white shadow"
                  />
                </button>
              </div>

              {/* Density */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Monitor size={14} className="text-gray-400" />
                  <span className="text-xs font-bold text-gray-300">UI Density</span>
                </div>
                <div className="flex gap-2">
                  {(['compact', 'normal', 'comfortable'] as const).map(d => (
                    <button
                      key={d}
                      onClick={() => update({ density: d })}
                      className={`flex-1 py-2 rounded-lg text-[10px] font-bold uppercase tracking-wide border transition-all ${
                        settings.density === d
                          ? 'bg-cyan-500/15 text-cyan-400 border-cyan-500/30'
                          : 'bg-white/5 text-gray-500 border-white/10 hover:text-gray-300'
                      }`}
                    >
                      {d}
                    </button>
                  ))}
                </div>
              </div>

              {/* Auto Refresh */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Sun size={14} className="text-gray-400" />
                  <span className="text-xs font-bold text-gray-300">Auto Refresh</span>
                </div>
                <button
                  onClick={() => update({ autoRefresh: !settings.autoRefresh })}
                  className={`w-10 h-5 rounded-full transition-all ${settings.autoRefresh ? 'bg-cyan-500' : 'bg-white/10'}`}
                >
                  <motion.div
                    animate={{ x: settings.autoRefresh ? 20 : 2 }}
                    className="w-4 h-4 rounded-full bg-white shadow"
                  />
                </button>
              </div>

              {settings.autoRefresh && (
                <div className="pl-6">
                  <div className="text-[10px] text-gray-500 mb-1">Refresh interval: {settings.refreshInterval / 1000}s</div>
                  <input
                    type="range"
                    min={3000}
                    max={30000}
                    step={1000}
                    value={settings.refreshInterval}
                    onChange={e => update({ refreshInterval: Number(e.target.value) })}
                    className="w-full accent-cyan-500"
                  />
                  <div className="flex justify-between text-[9px] text-gray-600">
                    <span>3s</span><span>30s</span>
                  </div>
                </div>
              )}
            </div>

            <div className="mt-6 pt-4 border-t border-white/5 text-[10px] text-gray-600 text-center">
              Wiki-Stream Intelligence v2.0 — Settings are saved for this session
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export type { Settings };
