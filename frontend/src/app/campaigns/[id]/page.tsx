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

export default function CampaignPage({ params }: Props) {
  const router = useRouter();
  const id = Number(params.id);
  const { data: campaign } = useSWR(`campaign-${id}`, () => api.getCampaign(id));
  const { data: creatives, isLoading, mutate } = useSWR(
    `campaign-${id}-creatives`,
    () => api.getCampaignCreatives(id)
  );

  const PTAG: Record<string, string> = {
    facebook: 'ptag-fb', google: 'ptag-gg', tiktok: 'ptag-tt',
    instagram: 'ptag-ig', linkedin: 'ptag-li', pinterest: 'ptag-pi',
  };

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
        <div className="tbl-wrap">
          <table>
            <thead>
              <tr>
                <th>Creative</th>
                <th>Format</th>
                <th style={{ width: 240 }}>AI Score</th>
                <th>Fatigue Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(creatives ?? []).map((c: CreativeSummary) => (
                <tr key={c.id} onClick={() => router.push(`/creatives/${c.id}`)}>
                  <td style={{ fontWeight: 500 }}>{c.filename}</td>
                  <td><span className="ftag">{c.format.toUpperCase()}</span></td>
                  <td><ScoreBar score={c.overall_score} /></td>
                  <td><FatigueBadge status={c.fatigue_status} /></td>
                  <td>
                    <button
                      className="btn btn-s btn-sm"
                      onClick={e => { e.stopPropagation(); router.push(`/creatives/${c.id}`); }}
                    >
                      View Detail
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
