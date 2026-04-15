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
  score_version?: string | null;
  alpha_score?: number | null;
  quality_score?: number | null;
  risk_score?: number | null;
  execution_score?: number | null;
  decision_score?: number | null;
  model_confidence?: number | null;
  evidence_confidence?: number | null;
  execution_confidence?: number | null;
  recommended_state?: string | null;
  paper_eligible?: boolean | null;
};

function pct(value: number | null | undefined) {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(1)}%`;
}

function num(value: number | null | undefined) {
  if (value === null || value === undefined) return '—';
  return value.toFixed(2);
}

export default function RecommendationCard({ row }: { row: RecommendationRow }) {
  return (
    <section style={{ border: '1px solid #eee', borderRadius: 10, padding: 16, display: 'grid', gap: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <h3 style={{ margin: 0 }}>{row.ticker}</h3>
          <div style={{ color: '#666', fontSize: 13 }}>{row.sector ?? '—'} • {row.industry_name ?? '—'}</div>
          <div style={{ color: '#888', fontSize: 12 }}>ICB {row.icb_code ?? '—'} • Industry {row.industry_code ?? '—'} • {row.score_version ?? 'legacy'}</div>
        </div>
        <div style={{ textAlign: 'right', color: '#666', fontSize: 13 }}>
          <div>{row.recommended_state ?? row.status}{row.paper_eligible ? ' ✅' : ''}</div>
          <div>{row.side} • {row.horizon}</div>
          <div>model {pct(row.model_confidence ?? row.confidence)}</div>
        </div>
      </div>
      <div><strong>Summary:</strong> {row.summary}</div>
      <div><strong>Why now:</strong> {row.why_now}</div>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', color: '#444', fontSize: 13 }}>
        <span>Decision {num(row.decision_score)}</span>
        <span>Alpha {num(row.alpha_score)}</span>
        <span>Quality {num(row.quality_score)}</span>
        <span>Risk {num(row.risk_score)}</span>
        <span>Exec {num(row.execution_score)}</span>
      </div>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', color: '#666', fontSize: 12 }}>
        <span>Evidence {pct(row.evidence_confidence)}</span>
        <span>Model {pct(row.model_confidence ?? row.confidence)}</span>
        <span>Execution {pct(row.execution_confidence)}</span>
        <span>Priority {row.suggested_priority}</span>
      </div>
    </section>
  );
}
