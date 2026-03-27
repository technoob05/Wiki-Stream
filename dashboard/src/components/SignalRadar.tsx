import { ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar } from 'recharts';

interface SignalData {
  rule: number;
  nlp: number;
  llm_conf: string;
  anomaly: number;
  reputation: number;
  graph?: number;
}

export const SignalRadar: React.FC<{ signals: SignalData }> = ({ signals }) => {
  const data = [
    { signal: 'RULE', value: Math.min(Number(signals.rule) * 10, 100), fullMark: 100 },
    { signal: 'NLP', value: Math.min(Number(signals.nlp) * 7, 100), fullMark: 100 },
    { signal: 'LLM', value: Math.min(Number(signals.llm_conf || 0) * 100, 100), fullMark: 100 },
    { signal: 'ANOMALY', value: Math.min(Number(signals.anomaly), 100), fullMark: 100 },
    { signal: 'REPUTE', value: Math.min(Number(signals.reputation), 100), fullMark: 100 },
    { signal: 'GRAPH', value: Math.min(Number(signals.graph || 0), 100), fullMark: 100 },
  ];

  return (
    <ResponsiveContainer width="100%" height={200}>
      <RadarChart data={data} cx="50%" cy="50%" outerRadius="75%">
        <PolarGrid stroke="rgba(255,255,255,0.08)" />
        <PolarAngleAxis
          dataKey="signal"
          tick={{ fill: '#6b7280', fontSize: 9, fontFamily: 'monospace' }}
        />
        <PolarRadiusAxis
          angle={30}
          domain={[0, 100]}
          tick={false}
          axisLine={false}
        />
        <Radar
          name="Signals"
          dataKey="value"
          stroke="#06b6d4"
          fill="#06b6d4"
          fillOpacity={0.2}
          strokeWidth={2}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
};
