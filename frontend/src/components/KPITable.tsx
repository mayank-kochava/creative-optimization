'use client';
import type { KPISummary } from '@/lib/api';

interface Props { kpi: KPISummary }

const fmt = (n: number | null, digits = 2, suffix = '') =>
  n !== null ? `${n.toFixed(digits)}${suffix}` : '—';

export function KPITable({ kpi }: Props) {
  const cells = [
    { label: 'Impressions', value: kpi.total_impressions.toLocaleString(), sub: 'total' },
    { label: 'Clicks', value: kpi.total_clicks.toLocaleString(), sub: 'total' },
    { label: 'CTR', value: fmt(kpi.ctr ? kpi.ctr * 100 : null, 2, '%'), sub: 'click-through rate' },
    { label: 'Installs', value: kpi.total_installs.toLocaleString(), sub: 'total' },
    { label: 'CVR', value: fmt(kpi.cvr ? kpi.cvr * 100 : null, 2, '%'), sub: 'conversion rate' },
    { label: 'Spend', value: `$${fmt(kpi.total_spend, 2)}`, sub: 'total' },
    { label: 'CPI', value: `$${fmt(kpi.cpi, 2)}`, sub: 'cost per install' },
    { label: 'Revenue', value: `$${fmt(kpi.total_revenue, 2)}`, sub: 'total' },
    { label: 'ROAS', value: fmt(kpi.roas, 2, 'x'), sub: 'return on ad spend' },
  ];

  return (
    <div className="kpi-g" style={{ gridTemplateColumns: 'repeat(3,1fr)' }}>
      {cells.map(c => (
        <div key={c.label} className="kpi-c">
          <div className="kpi-lbl">{c.label}</div>
          <div className="kpi-val">{c.value}</div>
          <div className="kpi-sub" style={{ color: 'var(--text-2)' }}>{c.sub}</div>
        </div>
      ))}
    </div>
  );
}
