'use client';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import { api, CreativeSummary } from '@/lib/api';
import { FatigueBadge } from '@/components/FatigueBadge';
import { CreativeUpload } from '@/components/CreativeUpload';

interface Props { params: { id: string } }

function ScoreBar({ score }: { score: number | null }) {
  if (score === null) return <span style={{ color: 'var(--text-3)', fontSize: 12 }}>Analysing…</span>;
  const cls = score >= 7 ? 'hi' : score >= 4 ? 'md' : 'lo';
  return (
    <div className="sbar">
      <div className="sbar-t"><div className={`sbar-f ${cls}`} style={{ width: `${score * 10}%` }} /></div>
      <span className="sn">{score}/10</span>
    </div>
  );
}

const FORMAT_GRADIENT: Record<string, string> = {
  mp4: 'linear-gradient(135deg,#0B1C0B,#14532D)',
  mov: 'linear-gradient(135deg,#0B1C0B,#14532D)',
  jpg: 'linear-gradient(135deg,#071121,#1e3a5f)',
  jpeg: 'linear-gradient(135deg,#071121,#1e3a5f)',
  png: 'linear-gradient(135deg,#1B0033,#4c1d95)',
  webp: 'linear-gradient(135deg,#1a1a2e,#6B21A8)',
  gif: 'linear-gradient(135deg,#1a0a0a,#7f1d1d)',
};

const PTAG: Record<string, string> = {
  facebook: 'ptag-fb', google: 'ptag-gg', tiktok: 'ptag-tt',
  instagram: 'ptag-ig', linkedin: 'ptag-li', pinterest: 'ptag-pi',
};

export default function CampaignPage({ params }: Props) {
  const router = useRouter();
  const id = Number(params.id);
  const { data: campaign } = useSWR(`campaign-${id}`, () => api.getCampaign(id));
  const { data: creatives, isLoading, mutate } = useSWR(
    `campaign-${id}-creatives`,
    () => api.getCampaignCreatives(id)
  );

  const isVideo = (fmt: string) => ['mp4', 'mov'].includes(fmt.toLowerCase());

  return (
    <div className="page">
      <div className="bc">
        <span className="bc-link" onClick={() => router.push('/')}>Dashboard</span>
        <span className="bc-sep">/</span>
        <span style={{ color: 'var(--text)' }}>{campaign?.name ?? '…'}</span>
      </div>

      <div className="pg-hdr">
        <div>
          <div className="pg-title">{campaign?.name ?? '…'}</div>
          <div className="pg-sub">
            {campaign?.platform_tags.map((t, i) => (
              <span key={t}>{i > 0 ? ' · ' : ''}<span className={`ptag ${PTAG[t] ?? 'ptag-gg'}`}>{t}</span></span>
            ))}
          </div>
        </div>
      </div>

      {creatives && (
        <div className="chips">
          <div className="chip"><span className="dot dot-blue" />{creatives.length} creatives</div>
          {creatives.filter(c => c.fatigue_status === 'fatiguing').length > 0 && (
            <div className="chip">
              <span className="dot dot-red" />
              {creatives.filter(c => c.fatigue_status === 'fatiguing').length} fatiguing
            </div>
          )}
        </div>
      )}

      <CreativeUpload campaignId={id} onSuccess={() => mutate()} />

      {isLoading ? (
        <div className="spin-wrap"><div className="spin" /></div>
      ) : (
        <div className="cr-grid">
          {(creatives ?? []).map((c: CreativeSummary) => (
            <div
              key={c.id}
              className="cr-card"
              onClick={() => router.push(`/creatives/${c.id}`)}
            >
              {/* Thumbnail */}
              <div
                className="cr-thumb"
                style={{ background: FORMAT_GRADIENT[c.format.toLowerCase()] ?? FORMAT_GRADIENT.jpg }}
              >
                {!isVideo(c.format) ? (
                  <img
                    src={`/api/creatives/${c.id}/image`}
                    alt={c.filename}
                    className="cr-thumb-img"
                    onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
                  />
                ) : (
                  <div className="cr-play">▶</div>
                )}
                <span className="cr-fmt-ov">{c.format.toUpperCase()}</span>
                {c.has_duplicate && <span className="cr-dup-ov">DUPE</span>}
              </div>

              {/* Info */}
              <div className="cr-body">
                <div className="cr-fname">{c.filename}</div>
                <ScoreBar score={c.overall_score} />
                <div className="cr-foot">
                  <FatigueBadge status={c.fatigue_status} />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
