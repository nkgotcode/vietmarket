type PolicyRow = { ticker: string; overall_result: string; blocking_flag: boolean; checks_json?: Array<{check_name:string;passed:boolean;blocking:boolean;detail:unknown}> | null };

export default function PolicyResultPanel({ rows }: { rows: PolicyRow[] }) {
  return (
    <div style={{ display: 'grid', gap: 12 }}>
      {rows.map((row) => (
        <section key={row.ticker} style={{ border: '1px solid #eee', borderRadius: 10, padding: 12, background: row.blocking_flag ? '#fff8f8' : undefined }}>
          <strong>{row.ticker}</strong> — {row.overall_result}
          <pre style={{ margin: '8px 0 0', padding: 12, borderRadius: 8, background: '#fafafa', overflowX: 'auto', fontSize: 12 }}>{JSON.stringify(row.checks_json ?? [], null, 2)}</pre>
        </section>
      ))}
      {rows.length===0 ? <p style={{color:'#666'}}>No policy results.</p> : null}
    </div>
  );
}
