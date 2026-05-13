interface Props {
  status: 'healthy' | 'fatiguing' | 'insufficient_data';
}

export function FatigueBadge({ status }: Props) {
  if (status === 'healthy') return <span className="badge badge-h">● Healthy</span>;
  if (status === 'fatiguing') return <span className="badge badge-f">⚠ Fatiguing</span>;
  return <span className="badge badge-i">Insufficient Data</span>;
}
