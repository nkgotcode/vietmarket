import SignalsDashboard from '@/components/signals/SignalsDashboard';

export default function SignalsPage() {
  return (
    <main style={{ maxWidth: 1280, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ marginTop: 0 }}>Signal engine</h1>
      <p style={{ color: '#666' }}>
        Phase 3 deterministic signal families and ranked candidate outputs built from the latest market-state cycle.
      </p>
      <SignalsDashboard />
    </main>
  );
}
