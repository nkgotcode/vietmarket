import RegimeDashboard from '@/components/market/RegimeDashboard';

export default function RegimePage() {
  return (
    <main style={{ maxWidth: 1200, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ marginTop: 0 }}>Market regime</h1>
      <p style={{ color: '#666' }}>
        Phase 2 Timescale/Postgres-backed market-state view showing the latest deterministic regime plus sector breadth.
      </p>
      <RegimeDashboard />
    </main>
  );
}
