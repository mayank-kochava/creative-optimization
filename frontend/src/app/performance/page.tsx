'use client';
import { useState, useMemo } from 'react';
import useSWR from 'swr';
import { useRouter } from 'next/navigation';
import { api, CreativeSummary } from '@/lib/api';
import { FatigueBadge } from '@/components/FatigueBadge';

const FORMAT_GRADIENT: Record<string, string> = {
  mp4: 'linear-gradient(135deg,#0B1C0B,#14532D)',
  mov: 'linear-gradient(135deg,#0B1C0B,#14532D)',
  jpg: 'linear-gradient(135deg,#071121,#1e3a5f)',
  jpeg: 'linear-gradient(135deg,#071121,#1e3a5f)',
  png: 'linear-gradient(135deg,#1B0033,#4c1d95)',
  webp: 'linear-gradient(135deg,#1a1a2e,#6B21A8)',
  gif: 'linear-gradient(135deg,#1a0a0a,#7f1d1d)',
};

const DURATIONS = [
  { label: '3 months', value: '3mo' },
  { label: '6 months', value: '6mo' },
  { label: '1 year', value: '1yr' },
];

const TOP_N_OPTIONS = [4, 6, 8, 10];

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

type PerfCreative = CreativeSummary & { ctr?: number; campaign_name?: string };

function PerfCard({ creative, cardCls }: { creative: PerfCreative; cardCls: string }) {
  const router = useRouter();
  const isVideo = ['mp4', 'mov'].includes(creative.format.toLowerCase());
  const grad = FORMAT_GRADIENT[creative.format.toLowerCase()] ?? FORMAT_GRADIENT.jpg;

  return (
    <div className={`cr-card ${cardCls}`} onClick={() => router.push(`/creatives/${creative.id}`)}>
      <div className="cr-thumb" style={{ background: grad }}>
        {!isVideo ? (
          <img
            src={`/api/creatives/${creative.id}/image`}
            alt={creative.filename}
            className="cr-thumb-img"
            onError={e => { (e.target as HTMLImageElement).style.display = 'none'; }}
          />
        ) : (
          <div className="cr-play">▶</div>
        )}
        <span className="cr-fmt-ov">{creative.format.toUpperCase()}</span>
        {creative.has_duplicate && <span className="cr-dup-ov">DUPE</span>}
        {creative.ctr != null && (
          <span style={{
            position: 'absolute', bottom: 12, left: 12,
            fontFamily: 'var(--font-m)', fontSize: 11, fontWeight: 700,
            color: 'rgba(255,255,255,.9)', background: 'rgba(0,0,0,.55)',
            padding: '3px 8px', borderRadius: 5, backdropFilter: 'blur(4px)',
          }}>
            CTR {creative.ctr.toFixed(2)}%
          </span>
        )}
      </div>
      <div className="cr-body">
        <div className="cr-fname">{creative.filename}</div>
        {creative.campaign_name && (
          <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: -4 }}>{creative.campaign_name}</div>
        )}
        <ScoreBar score={creative.overall_score} />
        <div className="cr-foot">
          <FatigueBadge status={creative.fatigue_status} />
        </div>
      </div>
    </div>
  );
}

export default function PerformancePage() {
  const [duration, setDuration] = useState('3mo');
  const [topN, setTopN] = useState(6);

  const { data: campaigns } = useSWR('campaigns', api.getCampaigns);
  const campaignIds = campaigns?.map(c => c.id) ?? [];

  const { data: allCreatives, isLoading } = useSWR(
    campaignIds.length > 0 ? `perf-creatives-${campaignIds.join('-')}` : null,
    async () => {
      const results = await Promise.all(
        campaignIds.map(id =>
          api.getCampaignCreatives(id).then(creatives =>
            creatives.map(c => ({
              ...c,
              campaign_name: campaigns?.find(camp => camp.id === id)?.name ?? '',
            }))
          )
        )
      );
      return results.flat();
    }
  );

  const { topCreatives, botCreatives } = useMemo(() => {
    if (!allCreatives) return { topCreatives: [], botCreatives: [] };
    const sorted = [...allCreatives].sort((a, b) =>
      ((b as PerfCreative).ctr ?? b.overall_score ?? 0) - ((a as PerfCreative).ctr ?? a.overall_score ?? 0)
    );
    return {
      topCreatives: sorted.slice(0, topN),
      botCreatives: sorted.slice(-topN).reverse(),
    };
  }, [allCreatives, topN]);

  return (
    <div className="page">
      <div className="pg-hdr">
        <div>
          <div className="pg-title">Performance</div>
          <div className="pg-sub">Compare top and bottom performing creatives across your portfolio</div>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24, flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', gap: 4, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 'var(--r)', padding: 3, boxShadow: 'var(--shadow)' }}>
          {DURATIONS.map(d => (
            <button
              key={d.value}
              className={`dur-btn${duration === d.value ? ' active' : ''}`}
              onClick={() => setDuration(d.value)}
            >
              {d.label}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-2)' }}>
          Show top/bottom
          <select
            value={topN}
            onChange={e => setTopN(Number(e.target.value))}
            style={{ border: '1px solid var(--border)', borderRadius: 'var(--r)', padding: '5px 10px', fontSize: 13, background: 'var(--surface)', color: 'var(--text)', cursor: 'pointer' }}
          >
            {TOP_N_OPTIONS.map(n => <option key={n} value={n}>{n}</option>)}
          </select>
          creatives
        </div>
      </div>

      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 4, height: 20, background: 'var(--green-border)', borderRadius: 2, display: 'inline-block' }} />
          Top Performers
        </div>
        {isLoading ? (
          <div className="spin-wrap"><div className="spin" /></div>
        ) : (
          <div className="cr-grid">
            {topCreatives.map(c => <PerfCard key={c.id} creative={c as PerfCreative} cardCls="top-card" />)}
          </div>
        )}
      </div>

      <div>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 4, height: 20, background: 'var(--red-border)', borderRadius: 2, display: 'inline-block' }} />
          Needs Attention
        </div>
        {isLoading ? (
          <div className="spin-wrap"><div className="spin" /></div>
        ) : (
          <div className="cr-grid">
            {botCreatives.map(c => <PerfCard key={c.id} creative={c as PerfCreative} cardCls="bot-card" />)}
          </div>
        )}
      </div>
    </div>
  );
}
