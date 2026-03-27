import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from 'recharts';

interface MassSourceChartProps {
  massSources: Record<string, { v: number; s: number; t: number }>;
  massCombined: { v: number; s: number; t: number };
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-[#0c0c10] border border-white/10 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-gray-400 mb-1 font-bold uppercase">{label}</p>
      {payload.map((p: any, i: number) => (
        <p key={i} className="font-mono" style={{ color: p.color }}>
          {p.name}: {(p.value * 100).toFixed(1)}%
        </p>
      ))}
    </div>
  );
};

export const MassSourceChart: React.FC<MassSourceChartProps> = ({ massSources, massCombined }) => {
  const data = [
    ...Object.entries(massSources).map(([source, masses]) => ({
      source: source.toUpperCase(),
      Vandalism: masses.v,
      Safe: masses.s,
      Uncertain: masses.t,
    })),
    {
      source: 'COMBINED',
      Vandalism: massCombined.v,
      Safe: massCombined.s,
      Uncertain: massCombined.t,
    },
  ];

  return (
    <ResponsiveContainer width="100%" height={180}>
      <BarChart data={data} barCategoryGap="20%">
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
        <XAxis
          dataKey="source"
          tick={{ fill: '#6b7280', fontSize: 9, fontFamily: 'monospace' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: '#6b7280', fontSize: 9 }}
          axisLine={false}
          tickLine={false}
          domain={[0, 1]}
          tickFormatter={(v: number) => `${(v * 100).toFixed(0)}%`}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: '10px', fontFamily: 'monospace' }}
          iconSize={8}
        />
        <Bar dataKey="Vandalism" fill="#ef4444" fillOpacity={0.8} radius={[2, 2, 0, 0]} stackId="stack" />
        <Bar dataKey="Safe" fill="#22c55e" fillOpacity={0.8} radius={[0, 0, 0, 0]} stackId="stack" />
        <Bar dataKey="Uncertain" fill="#6b7280" fillOpacity={0.5} radius={[2, 2, 0, 0]} stackId="stack" />
      </BarChart>
    </ResponsiveContainer>
  );
};
