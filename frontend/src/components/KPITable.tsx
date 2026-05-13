'use client';
import { Table, Typography } from 'antd';
import type { KPISummary } from '@/lib/api';

const { Text } = Typography;

interface Props {
  kpi: KPISummary;
}

const fmt = (n: number | null, digits = 2, suffix = '') =>
  n !== null ? `${n.toFixed(digits)}${suffix}` : '—';

export function KPITable({ kpi }: Props) {
  const summaryRows = [
    { metric: 'Impressions', value: kpi.total_impressions.toLocaleString() },
    { metric: 'Clicks', value: kpi.total_clicks.toLocaleString() },
    { metric: 'CTR', value: fmt(kpi.ctr ? kpi.ctr * 100 : null, 2, '%') },
    { metric: 'Installs', value: kpi.total_installs.toLocaleString() },
    { metric: 'CVR', value: fmt(kpi.cvr ? kpi.cvr * 100 : null, 2, '%') },
    { metric: 'Spend', value: `$${fmt(kpi.total_spend, 2)}` },
    { metric: 'CPI', value: `$${fmt(kpi.cpi, 2)}` },
    { metric: 'Revenue', value: `$${fmt(kpi.total_revenue, 2)}` },
    { metric: 'ROAS', value: fmt(kpi.roas, 2, 'x') },
  ];

  const columns = [
    { title: 'Metric', dataIndex: 'metric', key: 'metric', width: 120 },
    {
      title: 'Value (Last 30 Days)',
      dataIndex: 'value',
      key: 'value',
      render: (v: string) => <Text strong>{v}</Text>,
    },
  ];

  return (
    <Table
      dataSource={summaryRows}
      columns={columns}
      rowKey="metric"
      pagination={false}
      size="small"
    />
  );
}
