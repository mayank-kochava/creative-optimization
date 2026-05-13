# Task 19: Frontend Setup + API Client

**Files to create:**
- `frontend/package.json`
- `frontend/tsconfig.json`
- `frontend/next.config.js`
- `frontend/src/lib/api.ts`
- `frontend/src/app/AntdProviders.tsx` *(client component — Ant Design config)*
- `frontend/src/app/layout.tsx` *(server component — metadata export)*
- `frontend/src/app/globals.css`

**Prereq:** Node.js 20+ installed. Task 17 complete (backend API works).

---

## Step 1: Write test (TypeScript compile check)

```bash
# This is the "test" for frontend setup — TypeScript compiles cleanly
cd frontend && npx tsc --noEmit
```
Expected: FAIL — files don't exist yet.

---

## Step 2: Create `frontend/package.json`

```json
{
  "name": "creative-intelligence-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "next dev --port 3000",
    "build": "next build",
    "start": "next start",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "next": "14.2.3",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "antd": "5.17.0",
    "@ant-design/plots": "2.2.4",
    "@ant-design/nextjs-registry": "^1.0.1",
    "axios": "1.7.2",
    "swr": "2.2.5"
  },
  "devDependencies": {
    "typescript": "5.4.5",
    "@types/react": "18.3.3",
    "@types/react-dom": "18.3.0",
    "@types/node": "20.14.2"
  }
}
```

---

## Step 3: Create `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "target": "ES2017",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

---

## Step 4: Create `frontend/next.config.js`

```js
/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
```

---

## Step 5: Create `frontend/src/lib/api.ts`

```typescript
import axios from 'axios';

const client = axios.create({ baseURL: '/api' });

// --- Types ---

export interface Campaign {
  id: number;
  name: string;
  platform_tags: string[];
  creative_count: number;
  created_at: string;
  updated_at: string;
}

export interface AnalysisScores {
  hook_strength: number;
  cta_clarity: number;
  visual_quality: number;
  message_clarity: number;
  emotional_resonance: number;
  social_proof: number;
  brand_consistency: number;
}

export interface Analysis {
  scores: AnalysisScores;
  overall_score: number;
  persuasion_strategy: string;
  dominant_emotion: string;
  strengths: string[];
  weaknesses: string[];
  recommendations: string[];
  explanation: string;
  benchmark_percentile: number | null;
  status: 'complete' | 'degraded';
}

export interface Annotation {
  annotation_type: 'face' | 'text' | 'cta';
  bbox: { x: number; y: number; w: number; h: number };
  label: string | null;
  confidence: number;
}

export interface KPISummary {
  total_impressions: number;
  total_clicks: number;
  total_installs: number;
  total_spend: number;
  total_revenue: number;
  ctr: number | null;
  cvr: number | null;
  cpi: number | null;
  roas: number | null;
}

export interface Creative {
  id: number;
  campaign_id: number;
  filename: string;
  storage_path: string;
  format: string;
  width: number | null;
  height: number | null;
  duration_seconds: number | null;
  file_size_bytes: number;
  fatigue_status: 'healthy' | 'fatiguing' | 'insufficient_data';
  analysis: Analysis | null;
  annotations: Annotation[];
  kpi: KPISummary | null;
  created_at: string;
  updated_at: string;
}

export interface CreativeSummary {
  id: number;
  filename: string;
  format: string;
  width: number | null;
  height: number | null;
  fatigue_status: 'healthy' | 'fatiguing' | 'insufficient_data';
  overall_score: number | null;
  has_duplicate: boolean;
  created_at: string;
}

export interface UploadResponse {
  creative_id: number;
  duplicate_detected: boolean;
  duplicate_id: number | null;
  duplicate_type: string | null;
  hamming_distance: number | null;
  analysis_status: string;
}

export interface FatigueResponse {
  status: 'healthy' | 'fatiguing' | 'insufficient_data';
  daily_ctr: Array<{ date: string; ctr: number | null }>;
  threshold: number;
}

export interface DuplicatePair {
  id: number;
  creative_id_a: number;
  creative_id_b: number;
  hamming_distance: number;
  duplicate_type: string;
  detected_at: string;
}

// --- API calls ---

export const api = {
  getCampaigns: (): Promise<Campaign[]> =>
    client.get('/campaigns').then(r => r.data),

  getCampaign: (id: number): Promise<Campaign> =>
    client.get(`/campaigns/${id}`).then(r => r.data),

  createCampaign: (name: string, platform_tags: string[] = []): Promise<Campaign> =>
    client.post('/campaigns', { name, platform_tags }).then(r => r.data),

  getCampaignCreatives: (id: number, skip = 0, limit = 20): Promise<CreativeSummary[]> =>
    client.get(`/campaigns/${id}/creatives`, { params: { skip, limit } }).then(r => r.data),

  uploadCreative: (campaignId: number, file: File): Promise<UploadResponse> => {
    const form = new FormData();
    form.append('file', file);
    return client.post(`/campaigns/${campaignId}/creatives`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }).then(r => r.data);
  },

  getCreative: (id: number): Promise<Creative> =>
    client.get(`/creatives/${id}`).then(r => r.data),

  getFatigue: (id: number): Promise<FatigueResponse> =>
    client.get(`/creatives/${id}/fatigue`).then(r => r.data),

  getDuplicates: (id: number): Promise<DuplicatePair[]> =>
    client.get(`/creatives/${id}/duplicates`).then(r => r.data),
};
```

---

## Step 6a: Create `frontend/src/app/AntdProviders.tsx`

> **BUG FIX:** `layout.tsx` cannot have both `'use client'` and `export const metadata`.
> Extract all client-side Ant Design setup into a separate Client Component.

```tsx
'use client';
import { AntdRegistry } from '@ant-design/nextjs-registry';
import { ConfigProvider, Layout, Typography } from 'antd';

const { Header, Content } = Layout;
const { Title } = Typography;

export default function AntdProviders({ children }: { children: React.ReactNode }) {
  return (
    <AntdRegistry>
      <ConfigProvider
        theme={{
          token: {
            colorPrimary: '#1677ff',
            borderRadius: 6,
          },
        }}
      >
        <Layout style={{ minHeight: '100vh' }}>
          <Header style={{ display: 'flex', alignItems: 'center', background: '#001529' }}>
            <Title level={4} style={{ color: 'white', margin: 0 }}>
              Creative Intelligence Platform
            </Title>
          </Header>
          <Content style={{ padding: '24px' }}>
            {children}
          </Content>
        </Layout>
      </ConfigProvider>
    </AntdRegistry>
  );
}
```

---

## Step 6b: Create `frontend/src/app/layout.tsx`

> Server Component — no `'use client'` directive so `export const metadata` is valid.

```tsx
import type { Metadata } from 'next';
import './globals.css';
import AntdProviders from './AntdProviders';

export const metadata: Metadata = {
  title: 'Creative Intelligence Platform',
  description: 'AI-powered ad creative analysis',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AntdProviders>{children}</AntdProviders>
      </body>
    </html>
  );
}
```

---

## Step 7: Create `frontend/src/app/globals.css`

```css
* { box-sizing: border-box; }
body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
```

---

## Step 8: Add `@ant-design/nextjs-registry` dependency

```bash
cd frontend && npm install @ant-design/nextjs-registry
```

---

## Step 9: Install and verify TypeScript compiles

```bash
cd frontend && npm install && npx tsc --noEmit
```

Expected: 0 TypeScript errors.

---

## Step 10: Start dev server

```bash
cd frontend && npm run dev
```

Expected: `ready - started server on 0.0.0.0:3000` (page may 404 — that's OK, app/ pages come next).

---

## Step 11: Commit

```bash
git add frontend/
git commit -m "feat: Next.js 14 frontend setup — Ant Design 5, API client with full TypeScript types"
```
