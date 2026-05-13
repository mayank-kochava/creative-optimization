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
