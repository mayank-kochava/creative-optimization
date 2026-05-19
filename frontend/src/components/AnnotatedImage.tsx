'use client';
import type { Annotation } from '@/lib/api';

interface Props {
  imageUrl: string;
  annotations: Annotation[];
  width?: number;
  height?: number;
}

const COLORS: Record<Annotation['annotation_type'], string> = {
  face: '#1677ff',
  text: '#52c41a',
  cta: '#ff4d4f',
};

const LABELS: Record<Annotation['annotation_type'], string> = {
  face: 'Face',
  text: 'Text',
  cta: 'CTA',
};

export function AnnotatedImage({ imageUrl, annotations, width = 400, height = 300 }: Props) {
  // bbox coords are in original image pixel space; SVG viewBox maps them 1:1
  // so overlays scale correctly when img renders at a smaller display size
  const vb = `0 0 ${width} ${height}`;

  return (
    <div style={{ position: 'relative', display: 'inline-block', maxWidth: '100%', width: '100%' }}>
      <img
        src={imageUrl}
        alt="Creative"
        style={{ display: 'block', width: '100%', height: 'auto' }}
      />
      <svg
        viewBox={vb}
        style={{
          position: 'absolute', top: 0, left: 0,
          width: '100%', height: '100%',
          pointerEvents: 'none',
        }}
      >
        {annotations.map((ann, i) => {
          const color = COLORS[ann.annotation_type];
          const { x, y, w: bw, h: bh } = ann.bbox;
          const label = `${LABELS[ann.annotation_type]}${ann.label ? `: "${ann.label}"` : ''} (${(ann.confidence * 100).toFixed(0)}%)`;
          return (
            <g key={i}>
              <rect
                x={x} y={y} width={bw} height={bh}
                fill="none" stroke={color} strokeWidth={2}
                vectorEffect="non-scaling-stroke"
                style={{ pointerEvents: 'all', cursor: 'pointer' }}
              />
              {ann.annotation_type === 'cta' && (
                <text x={x} y={y - 4} fill={color} fontSize={10} fontWeight="bold">
                  CTA
                </text>
              )}
              <title>{label}</title>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
