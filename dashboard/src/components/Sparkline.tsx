import { useMemo } from 'react';

interface SparklineProps {
  data: number[];
  width?: number;
  height?: number;
  color?: string;
  filled?: boolean;
}

export const Sparkline: React.FC<SparklineProps> = ({
  data,
  width = 60,
  height = 20,
  color = '#06b6d4',
  filled = true,
}) => {
  const path = useMemo(() => {
    if (data.length < 2) return '';
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;
    const step = width / (data.length - 1);

    const points = data.map((v, i) => ({
      x: i * step,
      y: height - ((v - min) / range) * (height - 2) - 1,
    }));

    // Smooth curve using cubic bezier
    let d = `M ${points[0].x},${points[0].y}`;
    for (let i = 1; i < points.length; i++) {
      const prev = points[i - 1];
      const curr = points[i];
      const cpx = (prev.x + curr.x) / 2;
      d += ` C ${cpx},${prev.y} ${cpx},${curr.y} ${curr.x},${curr.y}`;
    }

    return d;
  }, [data, width, height]);

  const fillPath = useMemo(() => {
    if (!filled || !path) return '';
    return `${path} L ${width},${height} L 0,${height} Z`;
  }, [path, filled, width, height]);

  if (data.length < 2) return null;

  return (
    <svg width={width} height={height} className="overflow-visible">
      {filled && (
        <path d={fillPath} fill={color} fillOpacity={0.1} />
      )}
      <path d={path} fill="none" stroke={color} strokeWidth={1.5} strokeLinecap="round" />
      {/* End dot */}
      <circle
        cx={width}
        cy={(() => {
          const min = Math.min(...data);
          const max = Math.max(...data);
          const range = max - min || 1;
          return height - ((data[data.length - 1] - min) / range) * (height - 2) - 1;
        })()}
        r={2}
        fill={color}
      />
    </svg>
  );
};
