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
