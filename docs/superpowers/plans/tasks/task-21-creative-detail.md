# Task 21: Creative Detail Page + Components

**Files to create:**
- `frontend/src/app/creatives/[id]/page.tsx`
- `frontend/src/components/ScoreRadar.tsx`
- `frontend/src/components/AnnotatedImage.tsx`
- `frontend/src/components/KPITable.tsx`
- `frontend/src/components/DuplicateAlert.tsx`

**Prereq:** Task 20 complete.

---

## Step 1: Create `frontend/src/components/ScoreRadar.tsx`

```tsx
'use client';
import { Radar } from '@ant-design/plots';
import type { AnalysisScores } from '@/lib/api';

interface Props {
  scores: AnalysisScores;
}

const DIMENSION_LABELS: Record<keyof AnalysisScores, string> = {
  hook_strength: 'Hook Strength',
  cta_clarity: 'CTA Clarity',
  visual_quality: 'Visual Quality',
  message_clarity: 'Message Clarity',
  emotional_resonance: 'Emotional Resonance',
  social_proof: 'Social Proof',
  brand_consistency: 'Brand Consistency',
};

export function ScoreRadar({ scores }: Props) {
  const data = (Object.keys(scores) as Array<keyof AnalysisScores>).map(key => ({
    dimension: DIMENSION_LABELS[key],
    score: scores[key],
  }));

  const config = {
    data,
    xField: 'dimension',
    yField: 'score',
    area: { style: { fillOpacity: 0.3 } },
    scale: { y: { min: 0, max: 10, tickCount: 5 } },
    axis: {
      y: { gridAreaFill: 'rgba(0,0,0,0.04)', label: false, gridStroke: '#999' },
    },
    tooltip: { items: [{ field: 'score', name: 'Score' }] },
  };

  return <Radar {...config} style={{ height: 300 }} />;
}
```

---

## Step 2: Create `frontend/src/components/AnnotatedImage.tsx`

```tsx
'use client';
import { Tooltip } from 'antd';
import type { Annotation } from '@/lib/api';

interface Props {
  imageUrl: string;
  annotations: Annotation[];
  width?: number;
  height?: number;
}

const COLORS: Record<Annotation['annotation_type'], string> = {
  face: '#1677ff',
  text: '#52c41a',
  cta: '#ff4d4f',
};

const LABELS: Record<Annotation['annotation_type'], string> = {
  face: 'Face',
  text: 'Text',
  cta: 'CTA',
};

export function AnnotatedImage({ imageUrl, annotations, width = 400, height = 300 }: Props) {
  // BUG FIX: bbox coords are in original image pixel space. When the img renders
  // smaller (max-width: 100%), overlays misalign if we scale against original dims.
  // Solution: render inside an SVG with viewBox matching original dims so the
  // browser handles the scaling — overlays track the image exactly.
  const vb = `0 0 ${width} ${height}`;

  return (
    <div style={{ position: 'relative', display: 'inline-block', maxWidth: '100%', width: '100%' }}>
      <img
        src={imageUrl}
        alt="Creative"
        style={{ display: 'block', width: '100%', height: 'auto' }}
      />
      {/* SVG overlay stretches to match the img element; viewBox maps bbox coords 1:1 */}
      <svg
        viewBox={vb}
        style={{
          position: 'absolute', top: 0, left: 0,
          width: '100%', height: '100%',
          pointerEvents: 'none',
        }}
      >
        {annotations.map((ann, i) => {
          const color = COLORS[ann.annotation_type];
          const { x, y, w: bw, h: bh } = ann.bbox;
          const label = `${LABELS[ann.annotation_type]}${ann.label ? `: "${ann.label}"` : ''} (${(ann.confidence * 100).toFixed(0)}%)`;
          return (
            <g key={i}>
              <rect
                x={x} y={y} width={bw} height={bh}
                fill="none" stroke={color} strokeWidth={2}
                style={{ pointerEvents: 'all', cursor: 'pointer' }}
              />
              {ann.annotation_type === 'cta' && (
                <text x={x} y={y - 4} fill={color} fontSize={10} fontWeight="bold">
                  CTA
                </text>
              )}
              <title>{label}</title>
            </g>
          );
        })}
      </svg>
    </div>
  );
}


```

---

## Step 3: Create `frontend/src/components/KPITable.tsx`

```tsx
'use client';
import { Table, Typography } from 'antd';
import type { KPISummary } from '@/lib/api';

const { Text } = Typography;

interface Props {
  kpi: KPISummary;
}

const fmt = (n: number | null, digits = 2, suffix = '') =>
  n !== null ? `${n.toFixed(digits)}${suffix}` : '—';

export function KPITable({ kpi }: Props) {
  const summaryRows = [
    { metric: 'Impressions', value: kpi.total_impressions.toLocaleString() },
    { metric: 'Clicks', value: kpi.total_clicks.toLocaleString() },
    { metric: 'CTR', value: fmt(kpi.ctr ? kpi.ctr * 100 : null, 2, '%') },
    { metric: 'Installs', value: kpi.total_installs.toLocaleString() },
    { metric: 'CVR', value: fmt(kpi.cvr ? kpi.cvr * 100 : null, 2, '%') },
    { metric: 'Spend', value: `$${fmt(kpi.total_spend, 2)}` },
    { metric: 'CPI', value: `$${fmt(kpi.cpi, 2)}` },
    { metric: 'Revenue', value: `$${fmt(kpi.total_revenue, 2)}` },
    { metric: 'ROAS', value: fmt(kpi.roas, 2, 'x') },
  ];

  const columns = [
    { title: 'Metric', dataIndex: 'metric', key: 'metric', width: 120 },
    {
      title: 'Value (Last 30 Days)',
      dataIndex: 'value',
      key: 'value',
      render: (v: string) => <Text strong>{v}</Text>,
    },
  ];

  return (
    <Table
      dataSource={summaryRows}
      columns={columns}
      rowKey="metric"
      pagination={false}
      size="small"
    />
  );
}
```

---

## Step 4: Create `frontend/src/components/DuplicateAlert.tsx`

```tsx
import { Alert, Space } from 'antd';
import { useRouter } from 'next/navigation';
import type { DuplicatePair } from '@/lib/api';

interface Props {
  duplicates: DuplicatePair[];
  currentCreativeId: number;
}

export function DuplicateAlert({ duplicates, currentCreativeId }: Props) {
  const router = useRouter();
  if (!duplicates.length) return null;

  const description = (
    <Space direction="vertical">
      {duplicates.map(pair => {
        const otherId = pair.creative_id_a === currentCreativeId
          ? pair.creative_id_b
          : pair.creative_id_a;
        return (
          <span key={pair.id}>
            {pair.duplicate_type.replace('_', ' ')} duplicate of{' '}
            <a onClick={() => router.push(`/creatives/${otherId}`)}>
              Creative #{otherId}
            </a>
            {' '}(Hamming distance: {pair.hamming_distance})
          </span>
        );
      })}
    </Space>
  );

  return (
    <Alert
      type="warning"
      message={`${duplicates.length} duplicate${duplicates.length > 1 ? 's' : ''} detected`}
      description={description}
      showIcon
      style={{ marginBottom: 16 }}
    />
  );
}
```

---

## Step 5: Create `frontend/src/app/creatives/[id]/page.tsx`

```tsx
'use client';
import {
  Badge, Card, Col, Descriptions, List, Row, Space, Spin, Tag, Typography
} from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import { api } from '@/lib/api';
import { AnnotatedImage } from '@/components/AnnotatedImage';
import { DuplicateAlert } from '@/components/DuplicateAlert';
import { FatigueBadge } from '@/components/FatigueBadge';
import { KPITable } from '@/components/KPITable';
import { ScoreRadar } from '@/components/ScoreRadar';

const { Title, Paragraph, Text } = Typography;

interface Props {
  params: { id: string };
}

const STRATEGY_COLORS: Record<string, string> = {
  fear_appeal: 'red', fomo: 'orange', aspirational: 'blue',
  social_proof: 'green', rational: 'purple', unknown: 'default',
};

const EMOTION_COLORS: Record<string, string> = {
  excitement: 'gold', fear: 'red', trust: 'blue',
  joy: 'green', sadness: 'cyan', neutral: 'default', unknown: 'default',
};

export default function CreativeDetailPage({ params }: Props) {
  const router = useRouter();
  const creativeId = Number(params.id);
  const { data: creative, isLoading } = useSWR(
    `creative-${creativeId}`,
    () => api.getCreative(creativeId),
    { refreshInterval: creative?.analysis ? 0 : 3000 } // poll until analysis appears
  );
  const { data: duplicates = [] } = useSWR(
    `creative-${creativeId}-duplicates`,
    () => api.getDuplicates(creativeId)
  );

  if (isLoading || !creative) {
    return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />;
  }

  const imageUrl = `/api/creatives/${creativeId}/image`;

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <a onClick={() => router.back()}>
          <ArrowLeftOutlined /> Back
        </a>
        <Title level={4} style={{ margin: 0 }}>{creative.filename}</Title>
        <Tag>{creative.format.toUpperCase()}</Tag>
        {creative.width && <Text type="secondary">{creative.width}×{creative.height}</Text>}
        <FatigueBadge status={creative.fatigue_status} />
      </Space>

      <DuplicateAlert duplicates={duplicates} currentCreativeId={creativeId} />

      <Row gutter={[24, 24]}>
        {/* Left: image + annotations */}
        <Col xs={24} md={10}>
          <Card title="Creative Preview">
            <AnnotatedImage
              imageUrl={imageUrl}
              annotations={creative.annotations}
              width={creative.width ?? 400}
              height={creative.height ?? 300}
            />
          </Card>
        </Col>

        {/* Right: analysis */}
        <Col xs={24} md={14}>
          {!creative.analysis ? (
            <Card>
              <Spin tip="Analysing creative…" />
            </Card>
          ) : (
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Card title={`Overall Score: ${creative.analysis.overall_score}/10`}>
                <Space style={{ marginBottom: 16 }}>
                  <Tag color={STRATEGY_COLORS[creative.analysis.persuasion_strategy]}>
                    {creative.analysis.persuasion_strategy.replace(/_/g, ' ')}
                  </Tag>
                  <Tag color={EMOTION_COLORS[creative.analysis.dominant_emotion]}>
                    {creative.analysis.dominant_emotion}
                  </Tag>
                  {creative.analysis.benchmark_percentile && (
                    <Badge
                      count={`Top ${100 - creative.analysis.benchmark_percentile}%`}
                      style={{ backgroundColor: '#52c41a' }}
                    />
                  )}
                </Space>
                <ScoreRadar scores={creative.analysis.scores} />
              </Card>

              <Card title="Analysis">
                <Paragraph>{creative.analysis.explanation}</Paragraph>
                <Row gutter={16}>
                  <Col span={12}>
                    <Title level={5}>Strengths</Title>
                    <List
                      size="small"
                      dataSource={creative.analysis.strengths}
                      renderItem={item => <List.Item>✓ {item}</List.Item>}
                    />
                  </Col>
                  <Col span={12}>
                    <Title level={5}>Weaknesses</Title>
                    <List
                      size="small"
                      dataSource={creative.analysis.weaknesses}
                      renderItem={item => <List.Item>✗ {item}</List.Item>}
                    />
                  </Col>
                </Row>
              </Card>

              <Card title="Recommendations">
                <List
                  dataSource={creative.analysis.recommendations}
                  renderItem={(item, i) => (
                    <List.Item>
                      <Text strong>{i + 1}.</Text> {item}
                    </List.Item>
                  )}
                />
              </Card>
            </Space>
          )}
        </Col>
      </Row>

      {creative.kpi && (
        <Card title="Performance (Last 30 Days)" style={{ marginTop: 24 }}>
          <KPITable kpi={creative.kpi} />
        </Card>
      )}
    </div>
  );
}
```

---

## Step 6: Add image serve endpoint to backend

Add to `backend/app/routers/creatives.py`:

```python
from fastapi.responses import FileResponse

@router.get("/creatives/{creative_id}/image")
async def get_creative_image(creative_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Creative).where(Creative.id == creative_id))
    creative = result.scalar_one_or_none()
    if not creative:
        raise HTTPException(status_code=404, detail="Creative not found")
    path = Path(creative.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")
    return FileResponse(str(path))
```

---

## Step 7: Verify in browser

Navigate to `http://localhost:3000/creatives/1` → should show:
- Image with bounding boxes
- Score radar chart
- Strengths/weaknesses/recommendations
- KPI table

---

## Step 8: Commit

```bash
git add frontend/src/app/creatives/ frontend/src/components/
git commit -m "feat: creative detail page — annotated image, score radar, KPI table, duplicate alert"
```
