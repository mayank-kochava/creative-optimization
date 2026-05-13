'use client';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import { api } from '@/lib/api';
import { AnnotatedImage } from '@/components/AnnotatedImage';
import { DuplicateAlert } from '@/components/DuplicateAlert';
import { FatigueBadge } from '@/components/FatigueBadge';
import { KPITable } from '@/components/KPITable';
import { ScoreRadar } from '@/components/ScoreRadar';

interface Props { params: { id: string } }

export default function CreativeDetailPage({ params }: Props) {
  const router = useRouter();
  const creativeId = Number(params.id);

  const { data: creative, isLoading } = useSWR(
    `creative-${creativeId}`,
    () => api.getCreative(creativeId),
    { refreshInterval: (data) => (data?.analysis ? 0 : 3000) }
  );
  const { data: duplicates = [] } = useSWR(
    `creative-${creativeId}-duplicates`,
    () => api.getDuplicates(creativeId)
  );

  if (isLoading || !creative) {
    return <div className="spin-wrap"><div className="spin" /></div>;
  }

  const imageUrl = `/api/creatives/${creativeId}/image`;
  const score = creative.analysis?.overall_score ?? null;

  return (
    <div className="page">
      <div className="bc">
        <span className="bc-link" onClick={() => router.push('/')}>Dashboard</span>
        <span className="bc-sep">/</span>
        <span className="bc-link" onClick={() => router.back()}>Campaign</span>
        <span className="bc-sep">/</span>
        <span style={{ color: 'var(--text)' }}>{creative.filename}</span>
      </div>

      <div className="pg-hdr" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <div className="pg-title">{creative.filename}</div>
          <span className="ftag">{creative.format.toUpperCase()}</span>
          {creative.width && (
            <span style={{ color: 'var(--text-2)', fontSize: 13 }}>
              {creative.width}×{creative.height}
            </span>
          )}
          <FatigueBadge status={creative.fatigue_status} />
        </div>
      </div>

      <DuplicateAlert duplicates={duplicates} currentCreativeId={creativeId} />

      <div className="d-grid">
        {/* Left: image with annotations */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          <div className="panel">
            <div className="ph">
              Creative Preview
              <span className="ann-legend">
                <span><i style={{ border: '2px solid #1677FF' }} />Face</span>
                <span><i style={{ border: '2px solid #27AE60' }} />Text</span>
                <span><i style={{ border: '2px solid #C0392B' }} />CTA</span>
              </span>
            </div>
            <div className="pb" style={{ padding: 14 }}>
              <div className="img-wrap">
                <AnnotatedImage
                  imageUrl={imageUrl}
                  annotations={creative.annotations}
                  width={creative.width ?? 400}
                  height={creative.height ?? 300}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right: score + analysis */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {!creative.analysis ? (
            <div className="panel">
              <div className="pb" style={{ textAlign: 'center', padding: 40 }}>
                <div className="spin" style={{ margin: '0 auto 12px' }} />
                <div style={{ color: 'var(--text-2)', fontSize: 13 }}>Analysing creative…</div>
              </div>
            </div>
          ) : (
            <>
              {/* Score hero */}
              <div className="panel">
                <div className="score-hero">
                  <div className="score-big">
                    {score}<span className="score-denom">/10</span>
                  </div>
                  <div className="score-lbl">Overall Score</div>
                  <div className="a-tags">
                    <span className="atag atag-s">
                      {creative.analysis.persuasion_strategy.replace(/_/g, ' ')}
                    </span>
                    <span className="atag atag-e">
                      {creative.analysis.dominant_emotion}
                    </span>
                    {creative.analysis.benchmark_percentile && (
                      <span className="atag atag-p">
                        Top {100 - creative.analysis.benchmark_percentile}%
                      </span>
                    )}
                  </div>
                </div>
                <div className="radar-wrap">
                  <ScoreRadar scores={creative.analysis.scores} />
                </div>
              </div>

              {/* Analysis */}
              <div className="panel">
                <div className="ph">Analysis</div>
                <div className="pb">
                  <div className="expl">{creative.analysis.explanation}</div>
                  <div className="sw-g">
                    <div>
                      <div className="sw-h">Strengths</div>
                      {creative.analysis.strengths.map((s: string, i: number) => (
                        <div key={i} className="sw-row">
                          <span className="sw-ic ic-g">✓</span>{s}
                        </div>
                      ))}
                    </div>
                    <div>
                      <div className="sw-h">Weaknesses</div>
                      {creative.analysis.weaknesses.map((w: string, i: number) => (
                        <div key={i} className="sw-row">
                          <span className="sw-ic ic-r">✗</span>{w}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Recommendations */}
              <div className="panel">
                <div className="ph">Recommendations</div>
                <div className="pb">
                  <ul className="rec">
                    {creative.analysis.recommendations.map((r: string, i: number) => (
                      <li key={i}>
                        <span className="rec-n">{i + 1}</span>{r}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {creative.kpi && (
        <div className="panel" style={{ marginTop: 0 }}>
          <div className="ph">Performance — Last 30 Days</div>
          <div className="pb">
            <KPITable kpi={creative.kpi} />
          </div>
        </div>
      )}
    </div>
  );
}
