# Task 20: Dashboard + Campaign Pages

**Files to create:**
- `frontend/src/app/page.tsx`
- `frontend/src/app/campaigns/[id]/page.tsx`
- `frontend/src/components/CampaignCard.tsx`
- `frontend/src/components/CreativeUpload.tsx`
- `frontend/src/components/FatigueBadge.tsx`

**Prereq:** Task 19 complete (frontend setup, api.ts exists).

---

## Step 1: Verify test (manual — open browser)

After implementation, `http://localhost:3000` should show campaign list.
There are no automated tests for UI — verify manually.

---

## Step 2: Create `frontend/src/components/FatigueBadge.tsx`

Uses custom CSS badge classes — no Ant Design import needed for simple badges.

```tsx
interface Props {
  status: 'healthy' | 'fatiguing' | 'insufficient_data';
}

export function FatigueBadge({ status }: Props) {
  if (status === 'healthy') return <span className="badge badge-h">● Healthy</span>;
  if (status === 'fatiguing') return <span className="badge badge-f">⚠ Fatiguing</span>;
  return <span className="badge badge-i">Insufficient Data</span>;
}
```

---

## Step 3: Create `frontend/src/components/CampaignCard.tsx`

Custom CSS card — uses `.c-card`, `.c-name`, `.c-tags`, `.ptag`, `.c-foot`, `.c-stat` from globals.css.

```tsx
'use client';
import { useRouter } from 'next/navigation';
import type { Campaign } from '@/lib/api';

const PTAG: Record<string, string> = {
  facebook: 'ptag-fb', google: 'ptag-gg', tiktok: 'ptag-tt',
  instagram: 'ptag-ig', linkedin: 'ptag-li', pinterest: 'ptag-pi',
};

interface Props { campaign: Campaign }

export function CampaignCard({ campaign }: Props) {
  const router = useRouter();
  return (
    <div className="c-card" onClick={() => router.push(`/campaigns/${campaign.id}`)}>
      <div className="c-name">{campaign.name}</div>
      <div className="c-tags">
        {campaign.platform_tags.map(tag => (
          <span key={tag} className={`ptag ${PTAG[tag] ?? 'ptag-gg'}`}>{tag}</span>
        ))}
      </div>
      <div className="c-foot">
        <span className="c-stat"><b>{campaign.creative_count}</b> creatives</span>
        <span style={{ fontSize: 12, color: 'var(--text-3)' }}>View →</span>
      </div>
    </div>
  );
}
```

---

## Step 4: Create `frontend/src/components/CreativeUpload.tsx`

```tsx
'use client';
import { Alert, Upload, message } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { api, UploadResponse } from '@/lib/api';

const { Dragger } = Upload;

interface Props {
  campaignId: number;
  onSuccess: () => void;
}

export function CreativeUpload({ campaignId, onSuccess }: Props) {
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (file: File): Promise<boolean> => {
    setResult(null);
    setError(null);
    try {
      const resp = await api.uploadCreative(campaignId, file);
      setResult(resp);
      onSuccess();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Upload failed';
      setError(msg);
    }
    return false; // prevent default upload behavior
  };

  return (
    <div>
      <Dragger
        accept=".jpg,.jpeg,.png,.webp,.gif,.mp4,.mov"
        multiple={false}
        beforeUpload={handleUpload}
        showUploadList={false}
      >
        <p className="ant-upload-drag-icon"><InboxOutlined /></p>
        <p className="ant-upload-text">Click or drag creative to upload</p>
        <p className="ant-upload-hint">Supports: JPG, PNG, WebP, GIF, MP4, MOV · Max 20MB images, 500MB video</p>
      </Dragger>

      {result && !result.duplicate_detected && (
        <Alert
          style={{ marginTop: 12 }}
          type="info"
          message="Upload successful"
          description="Analysis queued — results appear within 15 seconds."
          showIcon
        />
      )}

      {result?.duplicate_detected && (
        <Alert
          style={{ marginTop: 12 }}
          type="warning"
          message={`Duplicate detected (Hamming distance: ${result.hamming_distance})`}
          description={
            <span>
              This creative is a {result.duplicate_type?.replace('_', ' ')} duplicate of creative #{result.duplicate_id}.
            </span>
          }
          showIcon
        />
      )}

      {error && (
        <Alert style={{ marginTop: 12 }} type="error" message="Upload failed" description={error} showIcon />
      )}
    </div>
  );
}
```

---

## Step 5: Create `frontend/src/app/page.tsx`

**Design decision**: No "Upload Creative" button here — uploading lives in campaign pages. The dashboard
is read-only navigation. Campaign cards ARE the primary action (click → campaign detail → upload there).

```tsx
'use client';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import { api } from '@/lib/api';
import { CampaignCard } from '@/components/CampaignCard';

export default function DashboardPage() {
  const router = useRouter();
  const { data: campaigns, isLoading } = useSWR('campaigns', api.getCampaigns);

  const fatiguing = campaigns?.filter(c => (c as any).fatiguing_count > 0).length ?? 0;

  return (
    <div className="page">
      <div className="pg-hdr">
        <div>
          <div className="pg-title">Campaigns</div>
          <div className="pg-sub">{campaigns?.length ?? 0} active campaigns across all platforms</div>
        </div>
      </div>

      {campaigns && (
        <div className="chips">
          <div className="chip"><span className="dot dot-blue" />{campaigns.length} campaigns</div>
          <div className="chip"><span className="dot dot-blue" />{campaigns.reduce((s, c) => s + c.creative_count, 0)} creatives</div>
          {fatiguing > 0 && (
            <div className="chip"><span className="dot dot-red" />{fatiguing} fatiguing</div>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="spin-wrap"><div className="spin" /></div>
      ) : !campaigns?.length ? (
        <div style={{ textAlign: 'center', padding: '80px 0', color: 'var(--text-2)' }}>
          No campaigns yet. Seed the database with <code>./dev.sh seed</code>
        </div>
      ) : (
        <div className="c-grid">
          {campaigns.map(c => <CampaignCard key={c.id} campaign={c} />)}
        </div>
      )}
    </div>
  );
}
```

---

## Step 6: Create `frontend/src/app/campaigns/[id]/page.tsx`

**Design decision**: Table replaced with visual card grid. Each card shows thumbnail preview
(gradient bg + real image via `/api/creatives/{id}/image`), format badge, DUPE badge,
score bar, fatigue badge. Cards are clickable → creative detail. Upload drop zone stays at top.

Card CSS lives in globals.css: `.cr-grid`, `.cr-card`, `.cr-thumb`, `.cr-body`, `.cr-foot`.
Card dimensions: 280px min-width, 210px thumbnail height (executive demo sizing).

```tsx
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
            <div key={c.id} className="cr-card" onClick={() => router.push(`/creatives/${c.id}`)}>
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
```

---

## Step 7: Verify in browser

```bash
cd backend && uvicorn app.main:app --reload --port 8000 &
cd frontend && npm run dev
```

Open `http://localhost:3000` → campaign cards grid.
Click a campaign → creative card grid (280px cards, 210px thumbnails, score bars, fatigue badges).
Click a card → creative detail page.

---

## Step 8: Commit

```bash
git add frontend/src/app/page.tsx frontend/src/app/campaigns/ frontend/src/components/ frontend/src/app/globals.css
git commit -m "feat: dashboard + campaign pages — campaign cards, creative card grid with thumbnails"
```
