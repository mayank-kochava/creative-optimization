'use client';
import { useState } from 'react';
import useSWR from 'swr';
import { api } from '@/lib/api';

const LABELS: Record<string, string> = {
  claude: 'Claude Sonnet 4.6',
  ollama: 'Qwen2.5-VL (Local)',
};

const ICONS: Record<string, string> = {
  claude: '◆',
  ollama: '⬡',
};

export function ProviderBadge() {
  const { data, mutate } = useSWR('provider', () => api.getProvider(), {
    refreshInterval: 0,
  });
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);

  if (!data) return null;

  const handleSwitch = async (name: string) => {
    if (name === data.active) { setOpen(false); return; }
    setSwitching(true);
    try {
      const updated = await api.setProvider(name);
      await mutate(updated, false);
    } finally {
      setSwitching(false);
      setOpen(false);
    }
  };

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '4px 10px', borderRadius: 20,
          border: '1px solid var(--border)',
          background: 'var(--surface)', cursor: 'pointer',
          fontSize: 12, color: 'var(--text-2)',
          fontFamily: 'inherit',
        }}
      >
        <span style={{ color: data.active === 'claude' ? '#7B61FF' : '#27AE60', fontSize: 10 }}>
          {ICONS[data.active] ?? '●'}
        </span>
        {LABELS[data.active] ?? data.active}
        <span style={{ fontSize: 9, opacity: 0.6 }}>▾</span>
      </button>

      {open && (
        <>
          <div
            onClick={() => setOpen(false)}
            style={{ position: 'fixed', inset: 0, zIndex: 99 }}
          />
          <div style={{
            position: 'absolute', top: 'calc(100% + 6px)', right: 0,
            background: 'var(--surface)', border: '1px solid var(--border)',
            borderRadius: 10, boxShadow: '0 4px 20px rgba(0,0,0,0.12)',
            minWidth: 200, zIndex: 100, overflow: 'hidden',
          }}>
            <div style={{ padding: '8px 12px 6px', fontSize: 11, color: 'var(--text-2)', fontWeight: 600, letterSpacing: '0.05em', textTransform: 'uppercase' }}>
              Analysis Model
            </div>
            {data.available.map(name => (
              <button
                key={name}
                disabled={switching}
                onClick={() => handleSwitch(name)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  width: '100%', padding: '8px 12px',
                  border: 'none', background: name === data.active ? 'var(--bg)' : 'transparent',
                  cursor: 'pointer', fontSize: 13, color: 'var(--text)',
                  fontFamily: 'inherit', textAlign: 'left',
                }}
              >
                <span style={{ color: name === 'claude' ? '#7B61FF' : '#27AE60', fontSize: 12 }}>
                  {ICONS[name] ?? '●'}
                </span>
                <div>
                  <div style={{ fontWeight: name === data.active ? 600 : 400 }}>
                    {LABELS[name] ?? name}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-2)' }}>
                    {name === 'claude' ? 'Anthropic API' : 'Local Ollama'}
                  </div>
                </div>
                {name === data.active && (
                  <span style={{ marginLeft: 'auto', color: 'var(--primary)', fontSize: 12 }}>✓</span>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
