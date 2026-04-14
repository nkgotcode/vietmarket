'use client';

import { useEffect, useState } from 'react';
import ApprovalQueue from '@/components/execution/ApprovalQueue';

type StagingPayload = {
  ok: boolean;
  staging: Array<Record<string, unknown>>;
  audits: Array<Record<string, unknown>>;
};

type ApprovalRow = { approval_id: string; staging_id: string; approval_status: string; approver: string | null; approval_json?: Record<string, unknown> | null };
type ApprovalPayload = {
  ok: boolean;
  rows: ApprovalRow[];
};

export default function ExecutionPage() {
  const [staging, setStaging] = useState<StagingPayload | null>(null);
  const [approvals, setApprovals] = useState<ApprovalPayload | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = () => {
    Promise.all([
      fetch('/api/brain/execution-staging', { cache: 'no-store' }).then((r)=>r.json() as Promise<StagingPayload>),
      fetch('/api/brain/approvals', { cache: 'no-store' }).then((r)=>r.json() as Promise<ApprovalPayload>),
    ]).then(([s,a]) => { setStaging(s); setApprovals(a); });
  };

  useEffect(() => {
    load();
  }, []);

  const handleAction = async (approvalId: string, action: 'approve' | 'reject') => {
    setBusyId(approvalId);
    await fetch('/api/brain/approvals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approval_id: approvalId, action, approver: 'operator-ui' }),
    });
    load();
    setBusyId(null);
  };

  return <main style={{ maxWidth: 1200, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}><h1 style={{ marginTop: 0 }}>Execution readiness</h1>{!staging || !approvals ? <p>Loading execution staging…</p> : <section style={{display:'grid',gap:16}}><pre style={{ margin:0, padding:12, borderRadius:8, background:'#fafafa', overflowX:'auto', fontSize:12 }}>{JSON.stringify(staging, null, 2)}</pre><ApprovalQueue rows={approvals.rows} onAction={handleAction} busyId={busyId} /></section>}</main>;
}
