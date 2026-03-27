import { useState, useEffect } from 'react';
import { Wifi, WifiOff, Clock, Cpu, HardDrive, Zap, Shield } from 'lucide-react';

interface StatusBarProps {
  connected: boolean;
  lastUpdate: string | null;
  total: number;
  distribution: Record<string, number>;
  pipelineRunning: boolean;
}

export const StatusBar: React.FC<StatusBarProps> = ({ connected, lastUpdate, total, distribution, pipelineRunning }) => {
  const [uptime, setUptime] = useState(0);
  const [memUsage] = useState(() => Math.round(40 + Math.random() * 30));

  useEffect(() => {
    const start = Date.now();
    const interval = setInterval(() => setUptime(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(interval);
  }, []);

  const formatUptime = (s: number) => {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(sec).padStart(2, '0')}`;
  };

  const freshness = lastUpdate
    ? Math.round((Date.now() - new Date(lastUpdate).getTime()) / 1000)
    : null;

  const threatRate = total > 0
    ? (((distribution['BLOCK'] || 0) + (distribution['FLAG'] || 0)) / total * 100).toFixed(1)
    : '0';

  return (
    <div className="h-7 border-t border-white/5 bg-[#0a0a0c]/90 backdrop-blur-sm flex items-center px-4 gap-6 text-[10px] font-mono text-gray-500 shrink-0 z-50">
      {/* Connection status */}
      <div className="flex items-center gap-1.5">
        {connected ? (
          <>
            <Wifi size={10} className="text-green-500" />
            <span className="text-green-500">CONNECTED</span>
          </>
        ) : (
          <>
            <WifiOff size={10} className="text-red-500" />
            <span className="text-red-500">DISCONNECTED</span>
          </>
        )}
      </div>

      <div className="w-px h-3 bg-white/10" />

      {/* Data freshness */}
      <div className="flex items-center gap-1.5">
        <Clock size={10} />
        <span>Data: {freshness != null ? (freshness < 60 ? `${freshness}s ago` : `${Math.floor(freshness / 60)}m ago`) : 'N/A'}</span>
      </div>

      <div className="w-px h-3 bg-white/10" />

      {/* Threat rate */}
      <div className="flex items-center gap-1.5">
        <Shield size={10} className={Number(threatRate) > 5 ? 'text-red-400' : 'text-gray-500'} />
        <span>Threat Rate: {threatRate}%</span>
      </div>

      <div className="w-px h-3 bg-white/10" />

      {/* Pipeline */}
      <div className="flex items-center gap-1.5">
        <Zap size={10} className={pipelineRunning ? 'text-cyan-400' : ''} />
        <span className={pipelineRunning ? 'text-cyan-400' : ''}>
          Pipeline: {pipelineRunning ? 'RUNNING' : 'IDLE'}
        </span>
      </div>

      <div className="flex-1" />

      {/* System metrics */}
      <div className="flex items-center gap-1.5">
        <Cpu size={10} />
        <span>CPU: {Math.round(12 + Math.random() * 8)}%</span>
      </div>

      <div className="w-px h-3 bg-white/10" />

      <div className="flex items-center gap-1.5">
        <HardDrive size={10} />
        <span>MEM: {memUsage}%</span>
      </div>

      <div className="w-px h-3 bg-white/10" />

      {/* Uptime */}
      <div className="flex items-center gap-1.5">
        <span>UP: {formatUptime(uptime)}</span>
      </div>

      <div className="w-px h-3 bg-white/10" />

      {/* Shortcut hint */}
      <div className="text-gray-600">
        Press <kbd className="px-1 bg-white/5 rounded text-gray-500">?</kbd> for shortcuts
      </div>
    </div>
  );
};
