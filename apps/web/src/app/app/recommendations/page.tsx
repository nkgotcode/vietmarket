import RecommendationsDashboard from '@/components/recommendations/RecommendationsDashboard';

export default function RecommendationsPage() {
  return (
    <main style={{ maxWidth: 1280, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ marginTop: 0 }}>Recommendations</h1>
      <p style={{ color: '#666' }}>
        Durable Phase 4 recommendation objects generated from the latest Phase 3 candidate and signal outputs.
      </p>
      <RecommendationsDashboard />
    </main>
  );
}
