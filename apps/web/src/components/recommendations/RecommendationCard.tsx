type RecommendationRow = {
  ticker: string;
  status: string;
  side: string;
  horizon: string;
  confidence: number;
  suggested_priority: number;
  summary: string;
  why_now: string;
  sector?: string | null;
  industry_name?: string | null;
  icb_code?: string | null;
  industry_code?: string | null;
};

function pct(value: number | null | undefined) {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(1)}%`;
}

export default function RecommendationCard({ row }: { row: RecommendationRow }) {
  return (
    <section style={{ border: '1px solid #eee', borderRadius: 10, padding: 16, display: 'grid', gap: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <h3 style={{ margin: 0 }}>{row.ticker}</h3>
          <div style={{ color: '#666', fontSize: 13 }}>{row.sector ?? '—'} • {row.industry_name ?? '—'}</div>
          <div style={{ color: '#888', fontSize: 12 }}>ICB {row.icb_code ?? '—'} • Industry {row.industry_code ?? '—'}</div>
        </div>
        <div style={{ textAlign: 'right', color: '#666', fontSize: 13 }}>
          <div>{row.status}</div>
          <div>{row.side} • {row.horizon}</div>
          <div>{pct(row.confidence)}</div>
        </div>
      </div>
      <div><strong>Summary:</strong> {row.summary}</div>
      <div><strong>Why now:</strong> {row.why_now}</div>
      <div style={{ color: '#666', fontSize: 12 }}>Priority {row.suggested_priority}</div>
    </section>
  );
}
