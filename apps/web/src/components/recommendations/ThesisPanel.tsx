type ThesisRow = {
  ticker: string;
  thesis_type: string;
  side: string;
  horizon: string;
  confidence: number;
  why_now: string;
  supporting_evidence?: Array<Record<string, unknown>>;
  contradicting_evidence?: Array<Record<string, unknown>>;
  invalidation?: Record<string, unknown>;
  notes?: string | null;
};

type RecommendationRow = {
  status: string;
  summary: string;
  confidence: number;
} | null;

function JsonBlock({ value }: { value: unknown }) {
  return (
    <pre style={{ margin: 0, padding: 12, borderRadius: 8, background: '#fafafa', overflowX: 'auto', fontSize: 12 }}>
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

export default function ThesisPanel({ thesis, recommendation }: { thesis: ThesisRow; recommendation: RecommendationRow }) {
  return (
    <section style={{ border: '1px solid #eee', borderRadius: 10, padding: 16, display: 'grid', gap: 12 }}>
      <div>
        <h2 style={{ margin: 0 }}>{thesis.ticker}</h2>
        <div style={{ color: '#666' }}>{thesis.thesis_type} • {thesis.side} • {thesis.horizon}</div>
        <div style={{ color: '#666' }}>Confidence {(thesis.confidence * 100).toFixed(1)}%</div>
      </div>
      {recommendation ? (
        <div style={{ color: '#666' }}>
          Recommendation: {recommendation.status} — {recommendation.summary}
        </div>
      ) : null}
      <div><strong>Why now:</strong> {thesis.why_now}</div>
      <div>
        <strong>Supporting evidence</strong>
        <JsonBlock value={thesis.supporting_evidence ?? []} />
      </div>
      <div>
        <strong>Contradicting evidence</strong>
        <JsonBlock value={thesis.contradicting_evidence ?? []} />
      </div>
      <div>
        <strong>Invalidation</strong>
        <JsonBlock value={thesis.invalidation ?? {}} />
      </div>
      {thesis.notes ? <div><strong>Notes:</strong> {thesis.notes}</div> : null}
    </section>
  );
}
