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
