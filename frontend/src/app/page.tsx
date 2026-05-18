'use client';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import { api } from '@/lib/api';
import { CampaignCard } from '@/components/CampaignCard';

export default function DashboardPage() {
  const router = useRouter();
  const { data: campaigns, isLoading } = useSWR('campaigns', api.getCampaigns);

  const fatiguing = campaigns?.filter(c => c.fatiguing_count > 0).length ?? 0;

  return (
    <div className="page">
      <div className="pg-hdr">
        <div>
          <div className="pg-title">Campaigns</div>
          <div className="pg-sub">{campaigns?.length ?? 0} active campaigns across all platforms</div>
        </div>
      </div>

      {campaigns && (
        <div className="chips">
          <div className="chip"><span className="dot dot-blue" />{campaigns.length} campaigns</div>
          <div className="chip"><span className="dot dot-blue" />{campaigns.reduce((s, c) => s + c.creative_count, 0)} creatives</div>
          {fatiguing > 0 && (
            <div className="chip"><span className="dot dot-red" />{fatiguing} fatiguing</div>
          )}
        </div>
      )}

      {isLoading ? (
        <div className="spin-wrap"><div className="spin" /></div>
      ) : !campaigns?.length ? (
        <div style={{ textAlign: 'center', padding: '80px 0', color: 'var(--text-2)' }}>
          No campaigns yet. Seed the database with <code>./dev.sh seed</code>
        </div>
      ) : (
        <div className="c-grid">
          {campaigns.map(c => <CampaignCard key={c.id} campaign={c} />)}
        </div>
      )}
    </div>
  );
}
