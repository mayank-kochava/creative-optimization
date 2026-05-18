'use client';
import { useRouter } from 'next/navigation';
import type { DuplicatePair } from '@/lib/api';

interface Props {
  duplicates: DuplicatePair[];
  currentCreativeId?: number;
}

export function DuplicateAlert({ duplicates }: Props) {
  const router = useRouter();
  if (!duplicates.length) return null;

  return (
    <div className="dup-alert">
      <span className="al-ic">⚠️</span>
      <div>
        <div className="al-ttl">
          {duplicates.length} duplicate{duplicates.length > 1 ? 's' : ''} detected
        </div>
        {duplicates.map(pair => (
          <div key={pair.duplicate_id} className="al-desc">
            {pair.duplicate_type.replace('_', ' ')} of{' '}
            <span className="al-link" onClick={() => router.push(`/creatives/${pair.duplicate_id}`)}>
              Creative #{pair.duplicate_id}
            </span>
            {' '}(Hamming distance: {pair.hamming_distance})
          </div>
        ))}
      </div>
    </div>
  );
}
