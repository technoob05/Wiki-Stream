import { motion } from 'framer-motion';

interface PignisticGaugeProps {
  vandalism: number;
  safe: number;
}

export const PignisticGauge: React.FC<PignisticGaugeProps> = ({ vandalism, safe }) => {
  const vPct = Math.round(vandalism * 100);
  const sPct = Math.round(safe * 100);

  // SVG arc gauge
  const radius = 60;
  const stroke = 10;
  const circumference = Math.PI * radius; // half circle
  const vLen = (vandalism) * circumference;
  const sLen = (safe) * circumference;

  return (
    <div className="flex flex-col items-center">
      <svg width={160} height={90} viewBox="0 0 160 90">
        {/* Background arc */}
        <path
          d="M 10 80 A 60 60 0 0 1 150 80"
          fill="none"
          stroke="rgba(255,255,255,0.05)"
          strokeWidth={stroke}
          strokeLinecap="round"
        />
        {/* Vandalism arc (from left) */}
        <motion.path
          d="M 10 80 A 60 60 0 0 1 150 80"
          fill="none"
          stroke="#ef4444"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${circumference}`}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - vLen }}
          transition={{ duration: 1, ease: 'easeOut' }}
        />
        {/* Safe arc (from right) */}
        <motion.path
          d="M 150 80 A 60 60 0 0 0 10 80"
          fill="none"
          stroke="#22c55e"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${circumference}`}
          initial={{ strokeDashoffset: circumference }}
          animate={{ strokeDashoffset: circumference - sLen }}
          transition={{ duration: 1, ease: 'easeOut', delay: 0.2 }}
        />
        {/* Center label */}
        <text x="80" y="65" textAnchor="middle" fill="white" fontSize="18" fontFamily="monospace" fontWeight="bold">
          {vPct}%
        </text>
        <text x="80" y="82" textAnchor="middle" fill="#9ca3af" fontSize="8" fontFamily="monospace">
          PIGNISTIC
        </text>
      </svg>
      <div className="flex gap-6 mt-1 text-[10px] font-mono">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-red-500" />
          <span className="text-red-400">Vandalism {vPct}%</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 rounded-full bg-green-500" />
          <span className="text-green-400">Safe {sPct}%</span>
        </div>
      </div>
    </div>
  );
};
