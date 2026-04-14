import HealthDashboard from '@/components/health/HealthDashboard';

export default function HealthPage() {
  return (
    <main style={{ maxWidth: 1200, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ marginTop: 0 }}>VietMarket Control Plane</h1>
      <p style={{ color: '#666' }}>
        Phase 1 health dashboard showing current platform status, dataset freshness, and recent worker activity.
      </p>
      <HealthDashboard />
    </main>
  );
}