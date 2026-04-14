type DeliveryEvent = {
  delivery_id: string;
  delivery_kind: string;
  channel: string;
  delivery_status: string;
  target_ref: string | null;
  created_at: string;
};

export default function DeliveryEventsTable({ rows }: { rows: DeliveryEvent[] }) {
  return (
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr>
          <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Kind</th>
          <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Channel</th>
          <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Status</th>
          <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Target</th>
          <th style={{ textAlign: 'left', borderBottom: '1px solid #e5e7eb', paddingBottom: 8 }}>Created</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={row.delivery_id}>
            <td style={{ paddingTop: 10 }}>{row.delivery_kind}</td>
            <td style={{ paddingTop: 10 }}>{row.channel}</td>
            <td style={{ paddingTop: 10 }}>{row.delivery_status}</td>
            <td style={{ paddingTop: 10 }}>{row.target_ref ?? 'n/a'}</td>
            <td style={{ paddingTop: 10 }}>{row.created_at}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
