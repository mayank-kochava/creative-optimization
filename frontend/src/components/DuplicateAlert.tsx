'use client';
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
