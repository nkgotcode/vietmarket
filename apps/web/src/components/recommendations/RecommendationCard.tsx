type RecommendationRow = {
  ticker: string;
  status: string;
  analytical_state?: string | null;
  policy_blocked?: boolean;
  side: string;
  horizon: string;
  suggested_priority: number;
  summary: string;
  why_now: string;
  sector?: string | null;
  industry_name?: string | null;
  icb_code?: string | null;
  industry_code?: string | null;
  score_version?: string | null;
  paper_eligible?: boolean | null;
  opportunity_grade?: string | null;
  evidence_grade?: string | null;
  tradability_grade?: string | null;
  risk_containment_grade?: string | null;
  forecast_reliability?: number | null;
  evidence_reliability?: number | null;
  execution_reliability?: number | null;
};

function pct(value: number | null | undefined) {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(1)}%`;
}

function grade(value: string | null | undefined) {
  return value && value.length > 0 ? value : '—';
}

export default function RecommendationCard({ row }: { row: RecommendationRow }) {
  return (
    <section style={{ border: '1px solid #eee', borderRadius: 10, padding: 16, display: 'grid', gap: 10 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
        <div>
          <h3 style={{ margin: 0 }}>{row.ticker}</h3>
          <div style={{ color: '#666', fontSize: 13 }}>{row.sector ?? '—'} • {row.industry_name ?? '—'}</div>
          <div style={{ color: '#888', fontSize: 12 }}>ICB {row.icb_code ?? '—'} • Industry {row.industry_code ?? '—'} • {row.score_version ?? 'grade-reset'}</div>
        </div>
        <div style={{ textAlign: 'right', color: '#666', fontSize: 13 }}>
          <div><strong>{row.status}</strong>{row.paper_eligible ? ' ✅' : ''}</div>
          <div>Analytical state: {row.analytical_state ?? '—'}</div>
          <div>Policy blocked: {row.policy_blocked ? 'yes' : 'no'}</div>
        </div>
      </div>

      <div><strong>Summary:</strong> {row.summary}</div>
      <div><strong>Why now:</strong> {row.why_now}</div>

      <div style={{ display: 'grid', gap: 6, gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', color: '#444', fontSize: 13 }}>
        <span><strong>Opportunity Grade</strong>: {grade(row.opportunity_grade)}</span>
        <span><strong>Evidence Grade</strong>: {grade(row.evidence_grade)}</span>
        <span><strong>Tradability Grade</strong>: {grade(row.tradability_grade)}</span>
        <span><strong>Risk Containment Grade</strong>: {grade(row.risk_containment_grade)}</span>
      </div>

      <div style={{ display: 'grid', gap: 6, gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', color: '#666', fontSize: 12 }}>
        <span><strong>Forecast Reliability</strong>: {pct(row.forecast_reliability)}</span>
        <span><strong>Evidence Reliability</strong>: {pct(row.evidence_reliability)}</span>
        <span><strong>Execution Reliability</strong>: {pct(row.execution_reliability)}</span>
        <span><strong>Priority</strong>: {row.suggested_priority}</span>
      </div>
    </section>
  );
}
