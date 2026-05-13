'use client';
import { Radar } from '@ant-design/plots';
import type { AnalysisScores } from '@/lib/api';

interface Props {
  scores: AnalysisScores;
}

const DIMENSION_LABELS: Record<keyof AnalysisScores, string> = {
  hook_strength: 'Hook Strength',
  cta_clarity: 'CTA Clarity',
  visual_quality: 'Visual Quality',
  message_clarity: 'Message Clarity',
  emotional_resonance: 'Emotional Resonance',
  social_proof: 'Social Proof',
  brand_consistency: 'Brand Consistency',
};

export function ScoreRadar({ scores }: Props) {
  const data = (Object.keys(scores) as Array<keyof AnalysisScores>).map(key => ({
    dimension: DIMENSION_LABELS[key],
    score: scores[key],
  }));

  const config = {
    data,
    xField: 'dimension',
    yField: 'score',
    area: { style: { fillOpacity: 0.3 } },
    scale: { y: { min: 0, max: 10, tickCount: 5 } },
    axis: {
      y: { gridAreaFill: 'rgba(0,0,0,0.04)', label: false, gridStroke: '#999' },
    },
    tooltip: { items: [{ field: 'score', name: 'Score' }] },
  };

  return <Radar {...config} style={{ height: 300 }} />;
}
