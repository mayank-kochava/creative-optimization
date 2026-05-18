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
    scale: { y: { domain: [0, 10] } },
    area: { style: { fillOpacity: 0.3 } },
    axis: {
      y: { label: false, gridStroke: '#ccc', tickCount: 5 },
    },
    tooltip: { items: [{ field: 'score', name: 'Score' }] },
    height: 300,
  };

  return <Radar {...config} />;
}
