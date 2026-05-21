'use client';
import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';
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

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null) return null;
  const pos = delta >= 0;
  return (
    <span className={`cr-delta ${pos ? 'cr-delta-pos' : 'cr-delta-neg'}`}>
      {pos ? '▲' : '▼'} {Math.abs(delta)}%
    </span>
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

function fmtCost(v: number | null) {
  if (v === null || v === 0) return null;
  return v >= 1000 ? `$${(v / 1000).toFixed(1)}k` : `$${v.toFixed(0)}`;
}

export default function CampaignPage({ params }: Props) {
  const router = useRouter();
  const id = Number(params.id);
  const { data: campaign } = useSWR(`campaign-${id}`, () => api.getCampaign(id));
  const { data: creatives, isLoading, mutate } = useSWR(
    `campaign-${id}-creatives`,
    () => api.getCampaignCreatives(id)
  );

  const [searchQ, setSearchQ] = useState('');
  const [formatFilter, setFormatFilter] = useState<'all' | 'image' | 'video'>('all');
  const [fatigueFilter, setFatigueFilter] = useState<'all' | 'fatiguing'>('all');

  const isVideo = (fmt: string) => ['mp4', 'mov'].includes(fmt.toLowerCase());

  const filtered = useMemo(() => {
    if (!creatives) return [];
    let list = creatives;

    if (formatFilter === 'video') list = list.filter(c => isVideo(c.format));
    else if (formatFilter === 'image') list = list.filter(c => !isVideo(c.format));

    if (fatigueFilter === 'fatiguing') list = list.filter(c => c.fatigue_status === 'fatiguing');

    if (searchQ.trim()) {
      const words = searchQ.toLowerCase().trim().split(/\s+/).filter(Boolean);
      list = list.filter(c => {
        const haystack = [
          ...(c.search_tags ?? []),
          c.filename,
        ].join(' ').toLowerCase();
        return words.every(w => haystack.includes(w));
      });
    }

    return list;
  }, [creatives, searchQ, formatFilter, fatigueFilter]);

  const fatigueCount = creatives?.filter(c => c.fatigue_status === 'fatiguing').length ?? 0;

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
          {fatigueCount > 0 && (
            <div className="chip"><span className="dot dot-red" />{fatigueCount} fatiguing</div>
          )}
        </div>
      )}

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
        </div>
      </div>

      <CreativeUpload campaignId={id} onSuccess={() => mutate()} />

      {isLoading ? (
        <div className="spin-wrap"><div className="spin" /></div>
      ) : (
        <>
          {searchQ && (
            <div className="cr-search-count">
              {filtered.length} result{filtered.length !== 1 ? 's' : ''} for &ldquo;{searchQ}&rdquo;
            </div>
          )}
          <div className="cr-grid">
            {filtered.map((c: CreativeSummary) => {
              const cost = fmtCost(c.cost_total);
              return (
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
                    {isVideo(c.format) && c.duration_seconds != null && (
                      <span className="cr-dur-ov">
                        {Math.floor(c.duration_seconds / 60)}:{String(Math.floor(c.duration_seconds % 60)).padStart(2, '0')}
                      </span>
                    )}
                  </div>

                  {/* Body */}
                  <div className="cr-body">
                    <div className="cr-fname">{c.filename}</div>
                    <ScoreBar score={c.overall_score} />

                    {/* Metrics grid */}
                    <div className="cr-metrics">
                      {c.ipm != null && (
                        <div className="cr-mrow">
                          <span className="cr-ml">IPM</span>
                          <span className="cr-mv">{c.ipm.toFixed(1)}</span>
                        </div>
                      )}
                      {c.ctr != null && (
                        <div className="cr-mrow">
                          <span className="cr-ml">CTR</span>
                          <span className="cr-mv">
                            {c.ctr.toFixed(1)}%
                            <DeltaBadge delta={c.ctr_delta_wow} />
                          </span>
                        </div>
                      )}
                      {cost && (
                        <div className="cr-mrow">
                          <span className="cr-ml">Cost</span>
                          <span className="cr-mv">{cost}</span>
                        </div>
                      )}
                      {c.days_active != null && (
                        <div className="cr-mrow">
                          <span className="cr-ml">Days</span>
                          <span className="cr-mv">{c.days_active}</span>
                        </div>
                      )}
                    </div>

                    <div className="cr-foot">
                      <FatigueBadge status={c.fatigue_status} />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
