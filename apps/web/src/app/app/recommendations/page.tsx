import RecommendationsDashboard from '@/components/recommendations/RecommendationsDashboard';

export default function RecommendationsPage() {
  return (
    <main style={{ maxWidth: 1280, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ marginTop: 0 }}>Recommendations</h1>
      <p style={{ color: '#666' }}>
        Durable recommendation objects generated from scoring v2 decision states, explicit promotion semantics, and bounded thesis context.
      </p>
      <RecommendationsDashboard />
    </main>
  );
}
