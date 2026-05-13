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
