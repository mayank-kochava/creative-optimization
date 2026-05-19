# Task 25: Frontend Brand Update + Performance Page

**Files to update/create:**
- `frontend/src/app/globals.css` — update CSS variables to Kochava brand tokens
- `frontend/src/app/layout.tsx` — update header background + nav
- `frontend/src/app/performance/page.tsx` — new Performance page

**Prereq:** Task 20 complete (dashboard + campaign pages exist).

---

## Goal

Make the frontend match the Kochava brand (K4A / frontend-mos) and add a Performance page showing top/bottom creatives ranked by CTR + AI score, with duration picker and configurable N.

---

## Step 1: Update CSS variables in `frontend/src/app/globals.css`

Find the `:root` block and replace these specific tokens:

```css
:root {
  --bg: #EDF1F7;              /* brand_background1 */
  --surface: #FFFFFF;
  --surface-2: #F4F6FA;
  --surface-3: #E8ECF3;
  --border: #E1E1E1;          /* grey_scale-grey4 */
  --border-h: #C4C9D4;
  --text: #1A1B1C;            /* grey_scale-black */
  --text-2: #575B5E;          /* grey_scale-grey1 */
  --text-3: #9DA3AE;
  --blue: #0C72EE;            /* brand_secondary — Kochava CTA blue */
  --blue-10: rgba(12,114,238,.08);
  --blue-20: rgba(12,114,238,.18);
  --blue-50: rgba(12,114,238,.5);
  --navy: #1E4B97;            /* brand_primary_1 */
  --green: #427900;
  --green-bg: #F3FAE8;
  --green-border: #4D840B;
  --red: #BE202E;
  --red-bg: #FFF3F2;
  --red-border: #E57373;
  --amber: #B07A00;
  --amber-bg: #FFF8E7;
  --amber-border: #F0C040;
  --r: 8px; --r-lg: 12px; --r-xl: 16px;
  --shadow: 0 1px 3px rgba(0,0,0,.08),0 1px 2px rgba(0,0,0,.06);
  --shadow-md: 0 4px 12px rgba(0,0,0,.10),0 2px 4px rgba(0,0,0,.06);
  --shadow-lg: 0 8px 30px rgba(0,0,0,.12);
  --font: 'Inter', var(--font-sans);
  --font-h: 'Inter', var(--font-sans);
  --font-m: var(--font-mono);
}
```

Also update the `@import` or `font-face` section if it references Syne/DM Sans — replace with Inter. The Next.js layout already imports fonts via `next/font`; just update the CSS variable references above.

Also add these two new CSS classes to the globals.css for the performance page:

```css
/* ── DURATION TOGGLE ── */
.dur-btn {
  padding: 5px 14px; border-radius: 6px; font-size: 12px; font-weight: 500;
  cursor: pointer; border: none; background: transparent; color: var(--text-2);
  font-family: var(--font); transition: all .15s;
}
.dur-btn:hover { color: var(--text); background: var(--surface-2); }
.dur-btn.active { background: var(--blue); color: #fff; font-weight: 600; }

/* ── PERFORMANCE CARD ACCENT ── */
.cr-card.top-card { border-left: 3px solid var(--green-border); }
.cr-card.bot-card { border-left: 3px solid var(--red-border); }
```

---

## Step 2: Update header in `frontend/src/app/layout.tsx`

Find the header element. Update:
- Header background: change from `#001529` (or whatever current value) to `#0F1E34`
- Logo orb gradient: `linear-gradient(135deg,#1E4B97,#0C72EE)`
- Add Performance nav link: `<Link href="/performance">Performance</Link>` after Campaigns

The nav should render: Dashboard · Campaigns · Performance

Read the file first to see current structure before editing.

---

## Step 3: Update Inter font import

Read `frontend/src/app/layout.tsx`. If it imports a different font (Syne, DM Sans), replace with Inter:

```tsx
import { Inter } from 'next/font/google';
const inter = Inter({ subsets: ['latin'], variable: '--font-sans' });
```

Apply to `<body className={inter.variable}>`.

---

## Step 4: Create `frontend/src/app/performance/page.tsx`

```tsx
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

function PerfCard({ creative, cardCls }: { creative: CreativeSummary & { ctr?: number; campaign_name?: string }; cardCls: string }) {
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

  // Fetch all campaigns then all their creatives
  const { data: campaigns } = useSWR('campaigns', api.getCampaigns);

  // Fetch creatives for all campaigns, merge into one flat list
  const campaignIds = campaigns?.map(c => c.id) ?? [];
  const { data: allCreatives } = useSWR(
    campaignIds.length > 0 ? `all-creatives-${campaignIds.join('-')}` : null,
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

  const sorted = useMemo(() => {
    if (!allCreatives) return [];
    // Sort by CTR descending (use kpi_summary.ctr if available, else overall_score as proxy)
    return [...allCreatives].sort((a, b) => {
      const aCtr = (a as any).ctr ?? (a.overall_score ?? 0);
      const bCtr = (b as any).ctr ?? (b.overall_score ?? 0);
      return bCtr - aCtr;
    });
  }, [allCreatives]);

  const topCreatives = sorted.slice(0, topN);
  const botCreatives = sorted.slice(-topN).reverse();

  return (
    <div className="page">
      <div className="pg-hdr">
        <div>
          <div className="pg-title">Performance</div>
          <div className="pg-sub">Compare top and bottom performing creatives across your portfolio</div>
        </div>
      </div>

      {/* Controls */}
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

      {/* Top performers */}
      <div style={{ marginBottom: 32 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 4, height: 20, background: 'var(--green-border)', borderRadius: 2, display: 'inline-block' }} />
          Top Performers
        </div>
        {!allCreatives ? (
          <div className="spin-wrap"><div className="spin" /></div>
        ) : (
          <div className="cr-grid">
            {topCreatives.map(c => <PerfCard key={c.id} creative={c as any} cardCls="top-card" />)}
          </div>
        )}
      </div>

      {/* Needs attention */}
      <div>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text)', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ width: 4, height: 20, background: 'var(--red-border)', borderRadius: 2, display: 'inline-block' }} />
          Needs Attention
        </div>
        {!allCreatives ? (
          <div className="spin-wrap"><div className="spin" /></div>
        ) : (
          <div className="cr-grid">
            {botCreatives.map(c => <PerfCard key={c.id} creative={c as any} cardCls="bot-card" />)}
          </div>
        )}
      </div>
    </div>
  );
}
```

---

## Step 5: Add `/performance` API endpoint (if missing)

Check `frontend/src/lib/api.ts`. If there's no `getPerformanceCreatives` method, the page fetches campaign-by-campaign which is fine for MVP. No backend changes needed — the page constructs the sorted list client-side from existing endpoints.

---

## Step 6: Verify

```bash
cd frontend && npm run dev
```

Open `http://localhost:3000`:
- Background should be `#EDF1F7` (warm light grey-blue, not white)
- Header should be `#0F1E34` (dark navy, slightly lighter than before)
- Buttons/links should be `#0C72EE` (Kochava blue)
- Nav shows: Dashboard · Campaigns · Performance

Open `http://localhost:3000/performance`:
- Duration picker renders (3 months active by default)
- Top/Bottom grids render with creative cards
- Top cards have green left border accent
- Bottom cards have red left border accent
- N selector changes grid count

---

## Step 7: Commit

```bash
git add frontend/src/app/globals.css frontend/src/app/layout.tsx frontend/src/app/performance/page.tsx
git commit -m "feat: Kochava brand tokens + Performance page"
```
