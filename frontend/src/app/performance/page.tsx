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

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null) return null;
  const pos = delta >= 0;
  return (
    <span className={`cr-delta ${pos ? 'cr-delta-pos' : 'cr-delta-neg'}`}>
      {pos ? '▲' : '▼'}{Math.abs(delta)}%
    </span>
  );
}

function fmtCost(v: number | null) {
  if (v === null || v === 0) return null;
  return v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(0)}`;
}

type PerfCreative = CreativeSummary & { campaign_name?: string };

function PerfCard({ creative, cardCls }: { creative: PerfCreative; cardCls: string }) {
  const router = useRouter();
  const isVideo = ['mp4', 'mov'].includes(creative.format.toLowerCase());
  const grad = FORMAT_GRADIENT[creative.format.toLowerCase()] ?? FORMAT_GRADIENT.jpg;
  const cost = fmtCost(creative.cost_total);

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
        {isVideo && creative.duration_seconds != null && (
          <span className="cr-dur-ov">
            {Math.floor(creative.duration_seconds / 60)}:{String(Math.floor(creative.duration_seconds % 60)).padStart(2, '0')}
          </span>
        )}
      </div>
      <div className="cr-body">
        <div className="cr-fname">{creative.filename}</div>
        {creative.campaign_name && (
          <div style={{ fontSize: 11, color: 'var(--text-3)', marginTop: -4 }}>{creative.campaign_name}</div>
        )}
        <ScoreBar score={creative.overall_score} />

        <div className="cr-metrics">
          {creative.ipm != null && (
            <div className="cr-mrow">
              <span className="cr-ml">IPM</span>
              <span className="cr-mv">{creative.ipm.toFixed(1)}</span>
            </div>
          )}
          {creative.ctr != null && (
            <div className="cr-mrow">
              <span className="cr-ml">CTR</span>
              <span className="cr-mv">
                {creative.ctr.toFixed(1)}%
                <DeltaBadge delta={creative.ctr_delta_wow} />
              </span>
            </div>
          )}
          {cost && (
            <div className="cr-mrow">
              <span className="cr-ml">Cost</span>
              <span className="cr-mv">{cost}</span>
            </div>
          )}
          {creative.days_active != null && (
            <div className="cr-mrow">
              <span className="cr-ml">Days</span>
              <span className="cr-mv">{creative.days_active}</span>
            </div>
          )}
        </div>

        <div className="cr-foot">
          <FatigueBadge status={creative.fatigue_status} />
        </div>
      </div>
    </div>
  );
}

export default function PerformancePage() {
  const [topN, setTopN] = useState(6);
  const [searchQ, setSearchQ] = useState('');
  const [formatFilter, setFormatFilter] = useState<'all' | 'image' | 'video'>('all');
  const [fatigueFilter, setFatigueFilter] = useState<'all' | 'fatiguing'>('all');

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

  const isVideo = (fmt: string) => ['mp4', 'mov'].includes(fmt.toLowerCase());

  const filtered = useMemo(() => {
    if (!allCreatives) return [];
    let list = allCreatives as PerfCreative[];

    if (formatFilter === 'video') list = list.filter(c => isVideo(c.format));
    else if (formatFilter === 'image') list = list.filter(c => !isVideo(c.format));

    if (fatigueFilter === 'fatiguing') list = list.filter(c => c.fatigue_status === 'fatiguing');

    if (searchQ.trim()) {
      const words = searchQ.toLowerCase().trim().split(/\s+/).filter(Boolean);
      list = list.filter(c => {
        const haystack = [
          ...(c.search_tags ?? []),
          c.filename,
          c.campaign_name ?? '',
        ].join(' ').toLowerCase();
        return words.every(w => haystack.includes(w));
      });
    }

    return list;
  }, [allCreatives, searchQ, formatFilter, fatigueFilter]);

  const { topCreatives, botCreatives } = useMemo(() => {
    const sorted = [...filtered].sort((a, b) =>
      (b.ctr ?? b.overall_score ?? 0) - (a.ctr ?? a.overall_score ?? 0)
    );
    return {
      topCreatives: sorted.slice(0, topN),
      botCreatives: sorted.slice(-topN).reverse(),
    };
  }, [filtered, topN]);

  return (
    <div className="page">
      <div className="pg-hdr">
        <div>
          <div className="pg-title">Performance</div>
          <div className="pg-sub">Top and bottom performing creatives across your portfolio</div>
        </div>
      </div>

      {/* Search + filters */}
      <div className="cr-search-wrap">
        <div className="cr-search">
          <svg className="cr-search-icon" viewBox="0 0 20 20" fill="none">
            <circle cx="8.5" cy="8.5" r="5.5" stroke="currentColor" strokeWidth="1.6"/>
            <path d="M13.5 13.5L17 17" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/>
          </svg>
          <input
            className="cr-search-input"
            placeholder="AI search — e.g. 'red background', 'outdoor scene', 'male character'…"
            value={searchQ}
            onChange={e => setSearchQ(e.target.value)}
          />
          {searchQ && (
            <button className="cr-search-clear" onClick={() => setSearchQ('')}>✕</button>
          )}
        </div>
        <div className="cr-filter-row">
          <span className="cr-filter-label">Format</span>
          {(['all', 'image', 'video'] as const).map(f => (
            <button
              key={f}
              className={`cr-filter-btn${formatFilter === f ? ' active' : ''}`}
              onClick={() => setFormatFilter(f)}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
          <span className="cr-filter-sep" />
          <span className="cr-filter-label">Status</span>
          <button
            className={`cr-filter-btn${fatigueFilter === 'all' ? ' active' : ''}`}
            onClick={() => setFatigueFilter('all')}
          >All</button>
          <button
            className={`cr-filter-btn cr-filter-btn-warn${fatigueFilter === 'fatiguing' ? ' active' : ''}`}
            onClick={() => setFatigueFilter(fatigueFilter === 'fatiguing' ? 'all' : 'fatiguing')}
          >Fatiguing</button>
          <span className="cr-filter-sep" />
          <span className="cr-filter-label">Show top/bottom</span>
          <select
            value={topN}
            onChange={e => setTopN(Number(e.target.value))}
            style={{ border: '1px solid var(--border)', borderRadius: 'var(--r)', padding: '4px 10px', fontSize: 12, background: 'var(--surface)', color: 'var(--text)', cursor: 'pointer' }}
          >
            {TOP_N_OPTIONS.map(n => <option key={n} value={n}>{n}</option>)}
          </select>
        </div>
        {searchQ && (
          <div className="cr-search-count">
            {filtered.length} result{filtered.length !== 1 ? 's' : ''} for &ldquo;{searchQ}&rdquo;
          </div>
        )}
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
            {topCreatives.map(c => <PerfCard key={c.id} creative={c} cardCls="top-card" />)}
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
            {botCreatives.map(c => <PerfCard key={c.id} creative={c} cardCls="bot-card" />)}
          </div>
        )}
      </div>
    </div>
  );
}
