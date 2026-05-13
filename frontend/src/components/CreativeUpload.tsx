'use client';
import { useRef, useState } from 'react';
import { api, UploadResponse } from '@/lib/api';

interface Props {
  campaignId: number;
  onSuccess: () => void;
  compact?: boolean;
}

export function CreativeUpload({ campaignId, onSuccess, compact = true }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  const upload = async (file: File) => {
    setResult(null); setError(null);
    try {
      const resp = await api.uploadCreative(campaignId, file);
      setResult(resp);
      onSuccess();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Upload failed');
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) upload(file);
  };

  return (
    <div>
      <input
        ref={inputRef} type="file"
        accept=".jpg,.jpeg,.png,.webp,.gif,.mp4,.mov"
        style={{ display: 'none' }}
        onChange={e => { const f = e.target.files?.[0]; if (f) upload(f); }}
      />

      {compact ? (
        <div
          className={`drop-compact${dragging ? ' drop-active' : ''}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <span className="drop-icon">📤</span>
          <div>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
              Drop creative here to upload
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-2)', marginTop: 2 }}>
              JPG · PNG · WebP · GIF · MP4 · MOV · Max 20MB image / 500MB video
            </div>
          </div>
        </div>
      ) : (
        <div
          className={`drop-big${dragging ? ' drop-active' : ''}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
        >
          <div className="icon">📤</div>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Click or drag to upload</div>
          <div style={{ fontSize: 12, color: 'var(--text-2)' }}>
            JPG · PNG · WebP · GIF · MP4 · MOV
          </div>
        </div>
      )}

      {result && !result.duplicate_detected && (
        <div style={{ marginTop: 10, padding: '10px 14px', background: 'var(--green-bg)', border: '1px solid var(--green-border)', borderRadius: 'var(--r)', fontSize: 13, color: 'var(--green)' }}>
          ✓ Upload successful — analysis queued, results in ~15 seconds.
        </div>
      )}

      {result?.duplicate_detected && (
        <div className="dup-alert" style={{ marginTop: 10, marginBottom: 0 }}>
          <span className="al-ic">⚠️</span>
          <div>
            <div className="al-ttl">Duplicate detected (Hamming: {result.hamming_distance})</div>
            <div className="al-desc">
              {result.duplicate_type?.replace('_', ' ')} of Creative #{result.duplicate_id}
            </div>
          </div>
        </div>
      )}

      {error && (
        <div style={{ marginTop: 10, padding: '10px 14px', background: 'var(--red-bg)', border: '1px solid var(--red-border)', borderRadius: 'var(--r)', fontSize: 13, color: 'var(--red)' }}>
          ✗ {error}
        </div>
      )}
    </div>
  );
}
