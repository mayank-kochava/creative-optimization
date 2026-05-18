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
    encode: { x: 'date', y: 'ctr' },
    style: { stroke: '#f5222d', lineWidth: 2 },
    point: { size: 3, shape: 'point' },
    smooth: true,
    axis: {
      y: {
        title: 'CTR %',
        labelFormatter: (v: number) => `${v}%`,
      },
    },
    tooltip: {
      items: [{ field: 'ctr', name: 'CTR', valueFormatter: (v: number) => `${v}%` }],
    },
    annotations: [
      {
        type: 'lineY',
        data: [+(threshold * 100).toFixed(2)],
        style: { stroke: '#faad14', lineDash: [4, 4], lineWidth: 1 },
      },
    ],
    height: 180,
  };

  return <Line {...config} />;
}
