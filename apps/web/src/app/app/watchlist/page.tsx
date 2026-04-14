import WatchlistDashboard from '@/components/market/WatchlistDashboard';

export default function WatchlistPage() {
  return (
    <main style={{ maxWidth: 1200, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ marginTop: 0 }}>Supervisor watchlist</h1>
      <p style={{ color: '#666' }}>
        Latest Phase 2 watchlist ranked from deterministic ticker snapshots, with canonical sector, industry, and code metadata visible directly in the table.
      </p>
      <WatchlistDashboard />
    </main>
  );
}
