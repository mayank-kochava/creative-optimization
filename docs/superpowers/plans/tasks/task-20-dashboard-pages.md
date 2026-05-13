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

```tsx
import { Tag } from 'antd';
import { WarningOutlined } from '@ant-design/icons';

interface Props {
  status: 'healthy' | 'fatiguing' | 'insufficient_data';
}

export function FatigueBadge({ status }: Props) {
  if (status === 'healthy') return <Tag color="green">Healthy</Tag>;
  if (status === 'fatiguing') return (
    <Tag color="red" icon={<WarningOutlined />}>Fatiguing</Tag>
  );
  return <Tag color="default">Insufficient Data</Tag>;
}
```

---

## Step 3: Create `frontend/src/components/CampaignCard.tsx`

```tsx
import { Card, Tag, Statistic, Space } from 'antd';
import { useRouter } from 'next/navigation';
import type { Campaign } from '@/lib/api';

interface Props {
  campaign: Campaign;
}

export function CampaignCard({ campaign }: Props) {
  const router = useRouter();
  return (
    <Card
      hoverable
      onClick={() => router.push(`/campaigns/${campaign.id}`)}
      style={{ marginBottom: 16 }}
      title={campaign.name}
      extra={
        <Space>
          {campaign.platform_tags.map(tag => (
            <Tag key={tag} color="blue">{tag}</Tag>
          ))}
        </Space>
      }
    >
      <Statistic title="Creatives" value={campaign.creative_count} />
    </Card>
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

```tsx
'use client';
import { Button, Col, Empty, Modal, Row, Spin, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useState } from 'react';
import useSWR from 'swr';
import { api } from '@/lib/api';
import { CampaignCard } from '@/components/CampaignCard';
import { CreativeUpload } from '@/components/CreativeUpload';

const { Title } = Typography;

export default function DashboardPage() {
  const { data: campaigns, isLoading, mutate } = useSWR('campaigns', api.getCampaigns);
  const [uploadCampaignId, setUploadCampaignId] = useState<number | null>(null);

  if (isLoading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />;

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col><Title level={3} style={{ margin: 0 }}>Campaigns</Title></Col>
        <Col>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setUploadCampaignId(campaigns?.[0]?.id ?? null)}
            disabled={!campaigns?.length}
          >
            Upload Creative
          </Button>
        </Col>
      </Row>

      {!campaigns?.length ? (
        <Empty description="No campaigns yet. Create one via the API or seed the database." />
      ) : (
        <Row gutter={[16, 16]}>
          {campaigns.map(campaign => (
            <Col key={campaign.id} xs={24} sm={12} md={8} lg={6}>
              <CampaignCard campaign={campaign} />
            </Col>
          ))}
        </Row>
      )}

      <Modal
        open={uploadCampaignId !== null}
        title="Upload Creative"
        footer={null}
        onCancel={() => setUploadCampaignId(null)}
      >
        {uploadCampaignId && (
          <CreativeUpload
            campaignId={uploadCampaignId}
            onSuccess={() => mutate()}
          />
        )}
      </Modal>
    </div>
  );
}
```

---

## Step 6: Create `frontend/src/app/campaigns/[id]/page.tsx`

```tsx
'use client';
import { Button, Progress, Space, Spin, Table, Tag, Typography } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import { api, CreativeSummary } from '@/lib/api';
import { FatigueBadge } from '@/components/FatigueBadge';
import { CreativeUpload } from '@/components/CreativeUpload';

const { Title } = Typography;

interface Props {
  params: { id: string };
}

export default function CampaignPage({ params }: Props) {
  const router = useRouter();
  const campaignId = Number(params.id);
  const { data: campaign } = useSWR(`campaign-${campaignId}`, () => api.getCampaign(campaignId));
  const { data: creatives, isLoading, mutate } = useSWR(
    `campaign-${campaignId}-creatives`,
    () => api.getCampaignCreatives(campaignId)
  );

  const columns = [
    {
      title: 'Name',
      dataIndex: 'filename',
      key: 'filename',
      render: (name: string, row: CreativeSummary) => (
        <a onClick={() => router.push(`/creatives/${row.id}`)}>{name}</a>
      ),
    },
    {
      title: 'Format',
      dataIndex: 'format',
      key: 'format',
      render: (f: string) => <Tag>{f.toUpperCase()}</Tag>,
    },
    {
      title: 'Score',
      dataIndex: 'overall_score',
      key: 'score',
      render: (score: number | null) =>
        score !== null
          ? <Progress percent={score * 10} size="small" format={() => `${score}/10`} />
          : <span style={{ color: '#999' }}>Analysing…</span>,
      sorter: (a: CreativeSummary, b: CreativeSummary) =>
        (a.overall_score ?? -1) - (b.overall_score ?? -1),
    },
    {
      title: 'Fatigue',
      dataIndex: 'fatigue_status',
      key: 'fatigue',
      render: (status: CreativeSummary['fatigue_status']) => <FatigueBadge status={status} />,
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_: unknown, row: CreativeSummary) => (
        <Button size="small" onClick={() => router.push(`/creatives/${row.id}`)}>
          View Detail
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push('/')}>Back</Button>
        <Title level={3} style={{ margin: 0 }}>{campaign?.name ?? '...'}</Title>
      </Space>

      <div style={{ marginBottom: 24 }}>
        <CreativeUpload campaignId={campaignId} onSuccess={() => mutate()} />
      </div>

      {isLoading ? (
        <Spin />
      ) : (
        <Table
          dataSource={creatives ?? []}
          columns={columns}
          rowKey="id"
          pagination={{ pageSize: 20 }}
        />
      )}
    </div>
  );
}
```

---

## Step 7: Verify in browser

```bash
# Backend must be running:
cd backend && uvicorn app.main:app --reload --port 8000 &
# Frontend:
cd frontend && npm run dev
```

Open `http://localhost:3000` → should show campaign cards.
Click a campaign → creative table with score progress bars and fatigue badges.

---

## Step 8: Commit

```bash
git add frontend/src/app/page.tsx frontend/src/app/campaigns/ frontend/src/components/
git commit -m "feat: dashboard + campaign pages — campaign cards, creative table, upload modal"
```
