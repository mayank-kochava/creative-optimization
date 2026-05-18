'use client';
import { Line } from '@ant-design/plots';

interface DataPoint {
  date: string;
  ctr: number | null;
}

interface Props {
  data: DataPoint[];
  threshold: number;
}

export function FatigueTrendChart({ data, threshold }: Props) {
  const points = data
    .filter(d => d.ctr !== null)
    .map(d => ({ date: d.date.slice(5), ctr: +(d.ctr! * 100).toFixed(2) }));

  if (points.length < 2) return null;

  const config = {
    data: points,
    xField: 'date',
    yField: 'ctr',
    smooth: true,
    point: { size: 3, shape: 'circle' as const },
    line: { style: { stroke: '#f5222d', lineWidth: 2 } },
    yAxis: {
      title: { text: 'CTR %' },
      label: { formatter: (v: string) => `${v}%` },
    },
    tooltip: {
      formatter: (d: { ctr: number }) => ({ name: 'CTR', value: `${d.ctr}%` }),
    },
    annotations: [
      {
        type: 'line' as const,
        start: ['min', threshold * 100] as [string, number],
        end: ['max', threshold * 100] as [string, number],
        style: { stroke: '#faad14', lineDash: [4, 4], lineWidth: 1 },
      },
    ],
    height: 180,
  };

  return <Line {...config} />;
}
