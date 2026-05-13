'use client';
import { Button, Col, Empty, Modal, Row, Spin, Typography } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { useState } from 'react';
import useSWR from 'swr';
import { api } from '@/lib/api';
import { CampaignCard } from '@/components/CampaignCard';
import { CreativeUpload } from '@/components/CreativeUpload';

const { Title } = Typography;

export default function DashboardPage() {
  const { data: campaigns, isLoading, mutate } = useSWR('campaigns', api.getCampaigns);
  const [uploadCampaignId, setUploadCampaignId] = useState<number | null>(null);

  if (isLoading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />;

  return (
    <div>
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col><Title level={3} style={{ margin: 0 }}>Campaigns</Title></Col>
        <Col>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setUploadCampaignId(campaigns?.[0]?.id ?? null)}
            disabled={!campaigns?.length}
          >
            Upload Creative
          </Button>
        </Col>
      </Row>

      {!campaigns?.length ? (
        <Empty description="No campaigns yet. Create one via the API or seed the database." />
      ) : (
        <Row gutter={[16, 16]}>
          {campaigns.map(campaign => (
            <Col key={campaign.id} xs={24} sm={12} md={8} lg={6}>
              <CampaignCard campaign={campaign} />
            </Col>
          ))}
        </Row>
      )}

      <Modal
        open={uploadCampaignId !== null}
        title="Upload Creative"
        footer={null}
        onCancel={() => setUploadCampaignId(null)}
      >
        {uploadCampaignId && (
          <CreativeUpload
            campaignId={uploadCampaignId}
            onSuccess={() => mutate()}
          />
        )}
      </Modal>
    </div>
  );
}
