type Approval = {
  approval_id: string;
  staging_id: string;
  approval_status: string;
  approver: string | null;
  approval_json?: Record<string, unknown> | null;
};

type Props = {
  rows: Approval[];
  onAction: (approvalId: string, action: 'approve' | 'reject') => Promise<void>;
  busyId: string | null;
};

export default function ApprovalQueue({ rows, onAction, busyId }: Props) {
  return (
    <div style={{ display: 'grid', gap: 12 }}>
      {rows.map((row) => (
        <div key={row.approval_id} style={{ border: '1px solid #e5e7eb', borderRadius: 10, padding: 12, background: '#fff' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 700 }}>{row.staging_id}</div>
              <div style={{ color: '#6b7280', fontSize: 14 }}>status={row.approval_status} approver={row.approver ?? 'pending'}</div>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button disabled={busyId === row.approval_id} onClick={() => void onAction(row.approval_id, 'approve')}>Approve</button>
              <button disabled={busyId === row.approval_id} onClick={() => void onAction(row.approval_id, 'reject')}>Reject</button>
            </div>
          </div>
          <pre style={{ margin: '12px 0 0', padding: 12, borderRadius: 8, background: '#fafafa', overflowX: 'auto', fontSize: 12 }}>{JSON.stringify(row.approval_json ?? {}, null, 2)}</pre>
        </div>
      ))}
    </div>
  );
}
