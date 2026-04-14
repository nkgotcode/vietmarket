type Props = {
  overallStatus: string;
  issueCount: number;
};

export default function SystemStatusBanner({ overallStatus, issueCount }: Props) {
  const background = overallStatus === 'blocked' ? '#ffe5e5' : overallStatus === 'degraded' ? '#fff5e0' : '#e8fff0';
  const color = overallStatus === 'blocked' ? '#8a1320' : overallStatus === 'degraded' ? '#8a5a00' : '#0a6a38';

  return (
    <div style={{ background, color, borderRadius: 10, padding: 16, border: `1px solid ${color}20` }}>
      <strong style={{ textTransform: 'capitalize' }}>{overallStatus}</strong>
      <span style={{ marginLeft: 8 }}>Open issues: {issueCount}</span>
    </div>
  );
}