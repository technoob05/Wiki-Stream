import {
  ResponsiveContainer,
  PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  AreaChart, Area,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  Treemap,
} from 'recharts';
import { TrendingUp, BarChart3, PieChart as PieIcon, Activity, Layers, Target } from 'lucide-react';
import { motion } from 'framer-motion';

interface AnalyticsProps {
  data: any;
}

const COLORS = {
  BLOCK: '#ef4444',
  FLAG: '#f97316',
  REVIEW: '#facc15',
  SAFE: '#22c55e',
};

const SectionTitle: React.FC<{ icon: any; title: string; subtitle?: string }> = ({ icon: Icon, title, subtitle }) => (
  <div className="flex items-center gap-3 mb-4">
    <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20">
      <Icon size={16} className="text-cyan-400" />
    </div>
    <div>
      <h3 className="text-sm font-bold text-white">{title}</h3>
      {subtitle && <p className="text-[10px] text-gray-500">{subtitle}</p>}
    </div>
  </div>
);

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#0c0c10] border border-white/10 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-gray-400 mb-1">{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} className="font-mono font-bold" style={{ color: p.color || '#06b6d4' }}>
          {p.name}: {typeof p.value === 'number' ? p.value.toLocaleString() : p.value}
        </p>
      ))}
    </div>
  );
};

export const AnalyticsView: React.FC<AnalyticsProps> = ({ data }) => {
  if (!data) return null;

  const dist = data.distribution || {};
  const stats = data.statistics || {};
  const threats = data.top_threats || [];

  // --- Pie chart data ---
  const pieData = Object.entries(dist).map(([name, value]) => ({
    name,
    value: value as number,
  }));
  const totalEdits = data.total || 0;

  // --- Score distribution histogram ---
  const buckets = [
    { range: '0-10', count: 0 },
    { range: '10-20', count: 0 },
    { range: '20-30', count: 0 },
    { range: '30-40', count: 0 },
    { range: '40-50', count: 0 },
    { range: '50-60', count: 0 },
    { range: '60-70', count: 0 },
    { range: '70-80', count: 0 },
    { range: '80-90', count: 0 },
    { range: '90-100', count: 0 },
  ];
  threats.forEach((t: any) => {
    const idx = Math.min(Math.floor(t.score / 10), 9);
    buckets[idx].count++;
  });

  // --- DS Belief distribution ---
  const beliefBuckets = Array.from({ length: 10 }, (_, i) => ({
    range: `${i * 10}-${(i + 1) * 10}%`,
    count: 0,
  }));
  threats.forEach((t: any) => {
    const idx = Math.min(Math.floor((t.ds_belief || 0) * 10), 9);
    beliefBuckets[idx].count++;
  });

  // --- Signal averages for radar ---
  const avgSignals = threats.length > 0 ? {
    rule: threats.reduce((s: number, t: any) => s + Number(t.signals?.rule || 0), 0) / threats.length,
    nlp: threats.reduce((s: number, t: any) => s + Number(t.signals?.nlp || 0), 0) / threats.length,
    anomaly: threats.reduce((s: number, t: any) => s + Number(t.signals?.anomaly || 0), 0) / threats.length,
    reputation: threats.reduce((s: number, t: any) => s + Number(t.signals?.reputation || 0), 0) / threats.length,
    llm_conf: threats.reduce((s: number, t: any) => s + Number(t.signals?.llm_conf || 0), 0) / threats.length,
  } : { rule: 0, nlp: 0, anomaly: 0, reputation: 0, llm_conf: 0 };

  const radarData = [
    { signal: 'RULE', value: avgSignals.rule * 10 },
    { signal: 'NLP', value: avgSignals.nlp * 7 },
    { signal: 'LLM', value: avgSignals.llm_conf * 100 },
    { signal: 'ANOMALY', value: avgSignals.anomaly },
    { signal: 'REPUTE', value: avgSignals.reputation },
  ];

  // --- Fusion method breakdown ---
  const fusionMethods = stats.fusion_methods || {};
  const fusionData = Object.entries(fusionMethods).map(([name, value]) => ({
    name,
    value: value as number,
  }));

  // --- Top users by threat count ---
  const userCounts: Record<string, { count: number; maxScore: number; actions: string[] }> = {};
  threats.forEach((t: any) => {
    if (!userCounts[t.user]) userCounts[t.user] = { count: 0, maxScore: 0, actions: [] };
    userCounts[t.user].count++;
    userCounts[t.user].maxScore = Math.max(userCounts[t.user].maxScore, t.score);
    if (!userCounts[t.user].actions.includes(t.action)) userCounts[t.user].actions.push(t.action);
  });
  const topUsers = Object.entries(userCounts)
    .sort((a, b) => b[1].count - a[1].count)
    .slice(0, 8)
    .map(([user, info]) => ({ user: user.length > 16 ? user.slice(0, 14) + '..' : user, edits: info.count, score: info.maxScore }));

  // --- Domain breakdown treemap ---
  const domainCounts: Record<string, number> = {};
  threats.forEach((t: any) => {
    const d = t.domain || 'unknown';
    domainCounts[d] = (domainCounts[d] || 0) + 1;
  });
  const treemapData = Object.entries(domainCounts).map(([name, size]) => ({ name, size }));

  // --- Cumulative score area chart ---
  const sortedByScore = [...threats].sort((a: any, b: any) => a.score - b.score);
  const cumulative = sortedByScore.map((t: any, i: number) => ({
    idx: i + 1,
    score: t.score,
    cumPct: Math.round(((i + 1) / sortedByScore.length) * 100),
  }));
  // Sample every Nth point for performance
  const step = Math.max(1, Math.floor(cumulative.length / 60));
  const sampledCumulative = cumulative.filter((_: any, i: number) => i % step === 0 || i === cumulative.length - 1);

  // --- Key stats cards ---
  const keyStats = [
    { label: 'Total Edits Analyzed', value: totalEdits.toLocaleString(), color: 'text-white' },
    { label: 'Blocked', value: (dist['BLOCK'] || 0).toLocaleString(), color: 'text-red-400' },
    { label: 'Flagged', value: (dist['FLAG'] || 0).toLocaleString(), color: 'text-orange-400' },
    { label: 'Under Review', value: (dist['REVIEW'] || 0).toLocaleString(), color: 'text-yellow-400' },
    { label: 'Safe', value: (dist['SAFE'] || 0).toLocaleString(), color: 'text-green-400' },
    { label: 'Avg Uncertainty', value: stats.avg_uncertainty?.toFixed(3) || 'N/A', color: 'text-purple-400' },
    { label: 'Avg Deng Entropy', value: stats.avg_deng_entropy?.toFixed(3) || 'N/A', color: 'text-blue-400' },
    { label: 'High-Conflict Edits', value: String(stats.high_conflict_edits || 0), color: 'text-red-400' },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white flex items-center gap-3">
              <BarChart3 size={22} className="text-cyan-400" /> Intelligence Analytics
            </h2>
            <p className="text-xs text-gray-500 mt-1">
              Comprehensive analysis of {totalEdits.toLocaleString()} edits across detection pipeline
            </p>
          </div>
          <div className="text-[10px] text-gray-500 font-mono">
            {data.timestamp ? new Date(data.timestamp).toLocaleString() : ''}
          </div>
        </div>

        {/* Key Stats Row */}
        <div className="grid grid-cols-4 xl:grid-cols-8 gap-3">
          {keyStats.map((s, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="p-3 rounded-xl bg-white/5 border border-white/10 text-center"
            >
              <div className="text-[9px] text-gray-500 font-bold uppercase tracking-widest mb-1">{s.label}</div>
              <div className={`font-mono font-bold text-lg ${s.color}`}>{s.value}</div>
            </motion.div>
          ))}
        </div>

        {/* Row 1: Distribution + Score Histogram */}
        <div className="grid grid-cols-2 gap-6">
          {/* Threat Distribution Donut */}
          <div className="rounded-xl bg-white/[0.03] border border-white/10 p-5">
            <SectionTitle icon={PieIcon} title="Threat Distribution" subtitle="Action verdicts across all analyzed edits" />
            <div className="flex items-center">
              <div className="flex-1">
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie
                      data={pieData}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={95}
                      paddingAngle={3}
                      dataKey="value"
                      strokeWidth={0}
                    >
                      {pieData.map((entry, i) => (
                        <Cell key={i} fill={COLORS[entry.name as keyof typeof COLORS] || '#6b7280'} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip />} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-3 ml-4">
                {pieData.map((entry, i) => {
                  const pct = totalEdits > 0 ? ((entry.value / totalEdits) * 100).toFixed(1) : '0';
                  return (
                    <div key={i} className="flex items-center gap-3">
                      <div className="w-3 h-3 rounded-sm" style={{ backgroundColor: COLORS[entry.name as keyof typeof COLORS] || '#6b7280' }} />
                      <span className="text-xs text-gray-400 font-mono w-16">{entry.name}</span>
                      <span className="text-xs font-bold text-white font-mono">{entry.value.toLocaleString()}</span>
                      <span className="text-[10px] text-gray-600 font-mono">({pct}%)</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>

          {/* Score Distribution */}
          <div className="rounded-xl bg-white/[0.03] border border-white/10 p-5">
            <SectionTitle icon={BarChart3} title="Threat Score Distribution" subtitle="Histogram of composite scores (0-100)" />
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={buckets} barCategoryGap="15%">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="range" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" name="Edits" radius={[4, 4, 0, 0]}>
                  {buckets.map((_, i) => (
                    <Cell key={i} fill={i < 3 ? '#22c55e' : i < 5 ? '#facc15' : i < 7 ? '#f97316' : '#ef4444'} fillOpacity={0.8} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Row 2: Radar + Fusion + Top Users */}
        <div className="grid grid-cols-3 gap-6">
          {/* Average Signal Radar */}
          <div className="rounded-xl bg-white/[0.03] border border-white/10 p-5">
            <SectionTitle icon={Target} title="Avg Signal Profile" subtitle="Mean signal strength across all threats" />
            <ResponsiveContainer width="100%" height={220}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="rgba(255,255,255,0.08)" />
                <PolarAngleAxis dataKey="signal" tick={{ fill: '#6b7280', fontSize: 10, fontFamily: 'monospace' }} />
                <PolarRadiusAxis tick={false} axisLine={false} domain={[0, 100]} />
                <Radar dataKey="value" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.2} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* Fusion Methods */}
          <div className="rounded-xl bg-white/[0.03] border border-white/10 p-5">
            <SectionTitle icon={Layers} title="Fusion Methods" subtitle="Evidence combination techniques used" />
            {fusionData.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={fusionData} layout="vertical" barCategoryGap="20%">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                  <XAxis type="number" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="name" tick={{ fill: '#9ca3af', fontSize: 11, fontFamily: 'monospace' }} axisLine={false} tickLine={false} width={70} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="value" name="Edits" fill="#8b5cf6" radius={[0, 4, 4, 0]} fillOpacity={0.8} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[220px] flex items-center justify-center text-gray-600 text-xs">No fusion data</div>
            )}
          </div>

          {/* Top Users */}
          <div className="rounded-xl bg-white/[0.03] border border-white/10 p-5">
            <SectionTitle icon={Activity} title="Top Flagged Users" subtitle="Users with most flagged edits" />
            <div className="space-y-2 mt-2">
              {topUsers.map((u, i) => {
                const maxCount = topUsers[0]?.edits || 1;
                const pct = (u.edits / maxCount) * 100;
                return (
                  <div key={i} className="flex items-center gap-3">
                    <span className="text-[10px] text-gray-500 font-mono w-4 text-right">{i + 1}</span>
                    <div className="flex-1">
                      <div className="flex justify-between items-center mb-0.5">
                        <span className="text-xs text-blue-400 font-mono">{u.user}</span>
                        <span className="text-[10px] text-gray-400 font-mono">{u.edits} edits</span>
                      </div>
                      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                        <motion.div
                          initial={{ width: 0 }}
                          animate={{ width: `${pct}%` }}
                          transition={{ duration: 0.8, delay: i * 0.05 }}
                          className="h-full rounded-full"
                          style={{ backgroundColor: u.score > 70 ? '#ef4444' : u.score > 40 ? '#f97316' : '#facc15' }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
              {topUsers.length === 0 && (
                <div className="text-gray-600 text-xs text-center py-8">No flagged users</div>
              )}
            </div>
          </div>
        </div>

        {/* Row 3: Cumulative Score + Belief Distribution */}
        <div className="grid grid-cols-2 gap-6">
          {/* Cumulative Score */}
          <div className="rounded-xl bg-white/[0.03] border border-white/10 p-5">
            <SectionTitle icon={TrendingUp} title="Score CDF" subtitle="Cumulative distribution of threat scores" />
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={sampledCumulative}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="score" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} label={{ value: 'Score', position: 'insideBottom', offset: -2, fill: '#6b7280', fontSize: 10 }} />
                <YAxis dataKey="cumPct" tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} domain={[0, 100]} label={{ value: '%', angle: -90, position: 'insideLeft', fill: '#6b7280', fontSize: 10 }} />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="cumPct" name="Cumulative %" stroke="#06b6d4" fill="#06b6d4" fillOpacity={0.1} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Belief Distribution */}
          <div className="rounded-xl bg-white/[0.03] border border-white/10 p-5">
            <SectionTitle icon={BarChart3} title="DS Belief Distribution" subtitle="Dempster-Shafer belief mass distribution" />
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={beliefBuckets} barCategoryGap="15%">
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis dataKey="range" tick={{ fill: '#6b7280', fontSize: 9 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#6b7280', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip content={<CustomTooltip />} />
                <Bar dataKey="count" name="Edits" fill="#22d3ee" radius={[4, 4, 0, 0]} fillOpacity={0.7} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Row 4: Domain Treemap */}
        {treemapData.length > 0 && (
          <div className="rounded-xl bg-white/[0.03] border border-white/10 p-5">
            <SectionTitle icon={Layers} title="Domain Distribution" subtitle="Edits by Wikipedia language domain" />
            <ResponsiveContainer width="100%" height={160}>
              <Treemap
                data={treemapData}
                dataKey="size"
                nameKey="name"
                stroke="rgba(255,255,255,0.1)"
                fill="#06b6d4"
                content={({ x, y, width, height, name, value }: any) => {
                  if (width < 40 || height < 25) return <rect x={x} y={y} width={width} height={height} fill="#06b6d4" fillOpacity={0.3} stroke="rgba(255,255,255,0.1)" />;
                  return (
                    <g>
                      <rect x={x} y={y} width={width} height={height} fill="#06b6d4" fillOpacity={0.2} stroke="rgba(255,255,255,0.1)" rx={4} />
                      <text x={x + width / 2} y={y + height / 2 - 6} textAnchor="middle" fill="#06b6d4" fontSize={11} fontFamily="monospace" fontWeight="bold">{name}</text>
                      <text x={x + width / 2} y={y + height / 2 + 10} textAnchor="middle" fill="#6b7280" fontSize={10} fontFamily="monospace">{value}</text>
                    </g>
                  );
                }}
              />
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
};
