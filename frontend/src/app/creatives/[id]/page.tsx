'use client';
import {
  Badge, Card, Col, List, Row, Space, Spin, Tag, Typography
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
    { refreshInterval: (data) => (data?.analysis ? 0 : 3000) }
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
        <a onClick={() => router.back()} style={{ cursor: 'pointer' }}>
          <ArrowLeftOutlined /> Back
        </a>
        <Title level={4} style={{ margin: 0 }}>{creative.filename}</Title>
        <Tag>{creative.format.toUpperCase()}</Tag>
        {creative.width && <Text type="secondary">{creative.width}×{creative.height}</Text>}
        <FatigueBadge status={creative.fatigue_status} />
      </Space>

      <DuplicateAlert duplicates={duplicates} currentCreativeId={creativeId} />

      <Row gutter={[24, 24]}>
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

        <Col xs={24} md={14}>
          {!creative.analysis ? (
            <Card>
              <Spin tip="Analysing creative…" />
            </Card>
          ) : (
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Card title={`Overall Score: ${creative.analysis.overall_score}/10`}>
                <Space style={{ marginBottom: 16 }}>
                  <Tag color={STRATEGY_COLORS[creative.analysis.persuasion_strategy] ?? 'default'}>
                    {creative.analysis.persuasion_strategy.replace(/_/g, ' ')}
                  </Tag>
                  <Tag color={EMOTION_COLORS[creative.analysis.dominant_emotion] ?? 'default'}>
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
                      renderItem={(item: string) => <List.Item>✓ {item}</List.Item>}
                    />
                  </Col>
                  <Col span={12}>
                    <Title level={5}>Weaknesses</Title>
                    <List
                      size="small"
                      dataSource={creative.analysis.weaknesses}
                      renderItem={(item: string) => <List.Item>✗ {item}</List.Item>}
                    />
                  </Col>
                </Row>
              </Card>

              <Card title="Recommendations">
                <List
                  dataSource={creative.analysis.recommendations}
                  renderItem={(item: string, i: number) => (
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
