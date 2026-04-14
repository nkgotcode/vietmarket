type SignalComponent = {
  component_name: string;
  component_value: number | null;
  component_weight: number | null;
  component_note: string | null;
};

type SignalRow = {
  signal_family: string;
  score_raw: number;
  score_normalized: number;
  confidence: number;
  blocking_flag: boolean;
  horizon: string;
  reason_json?: Record<string, unknown> | null;
  components: SignalComponent[];
};

type BreakdownRow = {
  ticker: string;
  sector: string | null;
  industry_name: string | null;
  ranking_bucket: string;
  total_score: number;
  total_confidence: number;
  signals: SignalRow[];
};

function pct(value: number | null) {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(1)}%`;
}

export default function SignalBreakdownTable({ rows }: { rows: BreakdownRow[] }) {
  return (
    <div style={{ display: 'grid', gap: 12 }}>
      {rows.map((row) => (
        <section key={row.ticker} style={{ border: '1px solid #eee', borderRadius: 10, padding: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline', marginBottom: 8 }}>
            <div>
              <strong>{row.ticker}</strong>
              <div style={{ color: '#666', fontSize: 12 }}>{row.sector ?? '—'} • {row.industry_name ?? '—'}</div>
            </div>
            <div style={{ color: '#666', fontSize: 12 }}>
              {row.ranking_bucket} • score {row.total_score.toFixed(2)} • confidence {pct(row.total_confidence)}
            </div>
          </div>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Family</th>
                <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Raw</th>
                <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Normalized</th>
                <th style={{ textAlign: 'right', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Confidence</th>
                <th style={{ textAlign: 'left', padding: '6px 4px', borderBottom: '1px solid #eee' }}>Components</th>
              </tr>
            </thead>
            <tbody>
              {row.signals.map((signal) => (
                <tr key={`${row.ticker}-${signal.signal_family}`} style={{ background: signal.blocking_flag ? '#fff8f8' : undefined }}>
                  <td style={{ padding: '6px 4px' }}>{signal.signal_family}{signal.blocking_flag ? ' (blocked)' : ''}</td>
                  <td style={{ padding: '6px 4px', textAlign: 'right' }}>{signal.score_raw.toFixed(2)}</td>
                  <td style={{ padding: '6px 4px', textAlign: 'right' }}>{pct(signal.score_normalized)}</td>
                  <td style={{ padding: '6px 4px', textAlign: 'right' }}>{pct(signal.confidence)}</td>
                  <td style={{ padding: '6px 4px' }}>
                    <div style={{ display: 'grid', gap: 2 }}>
                      {signal.components.map((component) => (
                        <div key={`${signal.signal_family}-${component.component_name}`} style={{ color: '#666' }}>
                          {component.component_name}: {component.component_value ?? '—'}
                          {component.component_note ? ` (${component.component_note})` : ''}
                        </div>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
      {rows.length === 0 ? <p style={{ color: '#666' }}>No signal breakdown rows available.</p> : null}
    </div>
  );
}
