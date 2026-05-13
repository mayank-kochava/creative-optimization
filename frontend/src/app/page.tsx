'use client';
import { useState } from 'react';
import useSWR from 'swr';
import { api } from '@/lib/api';
import { CampaignCard } from '@/components/CampaignCard';
import { CreativeUpload } from '@/components/CreativeUpload';

export default function DashboardPage() {
  const { data: campaigns, isLoading, mutate } = useSWR('campaigns', api.getCampaigns);
  const [modalOpen, setModalOpen] = useState(false);
  const [uploadCampaignId, setUploadCampaignId] = useState<number | null>(null);

  const openUpload = (id: number) => { setUploadCampaignId(id); setModalOpen(true); };
  const closeUpload = () => setModalOpen(false);

  const fatiguing = campaigns?.filter(c => (c as any).fatiguing_count > 0).length ?? 0;

  return (
    <div className="page">
      <div className="pg-hdr">
        <div>
          <div className="pg-title">Campaigns</div>
          <div className="pg-sub">{campaigns?.length ?? 0} active campaigns across all platforms</div>
        </div>
        <button
          className="btn btn-p"
          onClick={() => campaigns?.[0] && openUpload(campaigns[0].id)}
          disabled={!campaigns?.length}
        >
          ＋ Upload Creative
        </button>
      </div>

      {campaigns && (
        <div className="chips">
          <div className="chip"><span className="dot dot-blue" />{campaigns.length} campaigns</div>
          <div className="chip"><span className="dot dot-blue" />{campaigns.reduce((s, c) => s + c.creative_count, 0)} creatives</div>
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

      {/* Upload modal */}
      <div className={`overlay${modalOpen ? ' on' : ''}`} onClick={closeUpload}>
        <div className="modal" onClick={e => e.stopPropagation()}>
          <div className="m-title">
            Upload Creative
            <button className="modal-close" onClick={closeUpload}>✕</button>
          </div>
          <div className="m-sub">
            {campaigns?.find(c => c.id === uploadCampaignId)?.name}
          </div>
          {uploadCampaignId && (
            <CreativeUpload
              campaignId={uploadCampaignId}
              onSuccess={() => { mutate(); closeUpload(); }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
