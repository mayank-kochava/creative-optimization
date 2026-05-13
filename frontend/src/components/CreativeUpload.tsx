'use client';
import { Alert, Upload, message } from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import { useState } from 'react';
import { api, UploadResponse } from '@/lib/api';

const { Dragger } = Upload;

interface Props {
  campaignId: number;
  onSuccess: () => void;
}

export function CreativeUpload({ campaignId, onSuccess }: Props) {
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleUpload = async (file: File): Promise<boolean> => {
    setResult(null);
    setError(null);
    try {
      const resp = await api.uploadCreative(campaignId, file);
      setResult(resp);
      onSuccess();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || 'Upload failed';
      setError(msg);
    }
    return false;
  };

  return (
    <div>
      <Dragger
        accept=".jpg,.jpeg,.png,.webp,.gif,.mp4,.mov"
        multiple={false}
        beforeUpload={handleUpload}
        showUploadList={false}
      >
        <p className="ant-upload-drag-icon"><InboxOutlined /></p>
        <p className="ant-upload-text">Click or drag creative to upload</p>
        <p className="ant-upload-hint">Supports: JPG, PNG, WebP, GIF, MP4, MOV · Max 20MB images, 500MB video</p>
      </Dragger>

      {result && !result.duplicate_detected && (
        <Alert
          style={{ marginTop: 12 }}
          type="info"
          message="Upload successful"
          description="Analysis queued — results appear within 15 seconds."
          showIcon
        />
      )}

      {result?.duplicate_detected && (
        <Alert
          style={{ marginTop: 12 }}
          type="warning"
          message={`Duplicate detected (Hamming distance: ${result.hamming_distance})`}
          description={
            <span>
              This creative is a {result.duplicate_type?.replace('_', ' ')} duplicate of creative #{result.duplicate_id}.
            </span>
          }
          showIcon
        />
      )}

      {error && (
        <Alert style={{ marginTop: 12 }} type="error" message="Upload failed" description={error} showIcon />
      )}
    </div>
  );
}
