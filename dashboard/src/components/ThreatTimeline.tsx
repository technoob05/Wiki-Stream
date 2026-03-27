import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Shield } from 'lucide-react';

interface TimelineProps {
  threats: any[];
  onSelect: (threat: any) => void;
}

const actionColor: Record<string, string> = {
  BLOCK: '#ef4444',
  FLAG: '#f97316',
  REVIEW: '#facc15',
  SAFE: '#22c55e',
};

export const ThreatTimeline: React.FC<TimelineProps> = ({ threats, onSelect }) => {
  const sorted = useMemo(() => {
    return [...threats]
      .filter(t => t.timestamp)
      .sort((a, b) => Number(a.timestamp) - Number(b.timestamp));
  }, [threats]);

  if (sorted.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-gray-600 text-xs gap-2">
        <Shield size={16} /> No timeline data available
      </div>
    );
  }

  const minTime = Number(sorted[0].timestamp);
  const maxTime = Number(sorted[sorted.length - 1].timestamp);
  const range = maxTime - minTime || 1;

  // Group by hour for density visualization
  const hourBuckets: Record<number, { count: number; block: number; flag: number; review: number; safe: number }> = {};
  sorted.forEach(t => {
    const hour = Math.floor(Number(t.timestamp) / 3600) * 3600;
    if (!hourBuckets[hour]) hourBuckets[hour] = { count: 0, block: 0, flag: 0, review: 0, safe: 0 };
    hourBuckets[hour].count++;
    if (t.action === 'BLOCK') hourBuckets[hour].block++;
    else if (t.action === 'FLAG') hourBuckets[hour].flag++;
    else if (t.action === 'REVIEW') hourBuckets[hour].review++;
    else hourBuckets[hour].safe++;
  });

  const bucketEntries = Object.entries(hourBuckets).sort((a, b) => Number(a[0]) - Number(b[0]));
  const maxCount = Math.max(...bucketEntries.map(([, v]) => v.count));

  return (
    <div className="h-full flex flex-col">
      {/* Density bars */}
      <div className="flex-1 flex items-end gap-px px-4 pb-2 min-h-[120px]">
        {bucketEntries.map(([hour, data], i) => {
          const height = (data.count / maxCount) * 100;
          const blockPct = data.block / data.count * 100;
          const flagPct = data.flag / data.count * 100;
          const reviewPct = data.review / data.count * 100;

          return (
            <motion.div
              key={hour}
              initial={{ height: 0 }}
              animate={{ height: `${Math.max(height, 4)}%` }}
              transition={{ duration: 0.5, delay: i * 0.02 }}
              className="flex-1 rounded-t-sm cursor-pointer group relative overflow-hidden"
              style={{ minWidth: 3 }}
              title={`${new Date(Number(hour) * 1000).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })} — ${data.count} edits`}
            >
              {/* Stacked segments */}
              <div className="absolute inset-0 flex flex-col-reverse">
                <div style={{ height: `${100 - blockPct - flagPct - reviewPct}%` }} className="bg-green-500/40" />
                <div style={{ height: `${reviewPct}%` }} className="bg-yellow-500/60" />
                <div style={{ height: `${flagPct}%` }} className="bg-orange-500/70" />
                <div style={{ height: `${blockPct}%` }} className="bg-red-500/80" />
              </div>

              {/* Hover tooltip */}
              <div className="absolute -top-16 left-1/2 -translate-x-1/2 bg-black/90 border border-white/10 rounded-lg px-2 py-1 text-[10px] whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10">
                <div className="text-white font-bold">
                  {new Date(Number(hour) * 1000).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
                </div>
                <div className="text-gray-400">{data.count} edits</div>
                {data.block > 0 && <div className="text-red-400">{data.block} blocked</div>}
                {data.flag > 0 && <div className="text-orange-400">{data.flag} flagged</div>}
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Time axis */}
      <div className="flex justify-between px-4 py-1 border-t border-white/5">
        <span className="text-[10px] text-gray-600 font-mono">
          {new Date(minTime * 1000).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
        </span>
        <span className="text-[10px] text-gray-600 font-mono">
          {new Date(maxTime * 1000).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>

      {/* Legend */}
      <div className="flex gap-4 px-4 py-2 border-t border-white/5">
        {[
          { label: 'BLOCK', color: 'bg-red-500' },
          { label: 'FLAG', color: 'bg-orange-500' },
          { label: 'REVIEW', color: 'bg-yellow-500' },
          { label: 'SAFE', color: 'bg-green-500' },
        ].map(l => (
          <div key={l.label} className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-sm ${l.color}`} />
            <span className="text-[9px] text-gray-500 font-mono">{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
};
