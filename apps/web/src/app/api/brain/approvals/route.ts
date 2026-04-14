import { NextResponse } from 'next/server';
import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

type ApprovalActionBody = {
  approval_id?: string;
  action?: 'approve' | 'reject';
  approver?: string;
  reason?: string;
};

export async function GET(req: Request) {
  const denied = await requireAppAuth(req);
  if (denied) return denied;

  const pool = getPgPool();
  const result = await pool.query(`
    SELECT a.approval_id, a.staging_id, a.approval_status, a.approver, a.approval_json, a.created_at,
           s.ticker, s.side, s.qty, s.stage_status
    FROM execution_approvals a
    JOIN broker_order_staging s ON s.staging_id = a.staging_id
    ORDER BY a.created_at DESC
    LIMIT 100
  `);

  return NextResponse.json({ ok: true, rows: result.rows });
}

export async function POST(req: Request) {
  const denied = await requireAppAuth(req);
  if (denied) return denied;

  const body = (await req.json().catch(() => null)) as ApprovalActionBody | null;
  const approvalId = body?.approval_id;
  const action = body?.action;
  const approver = body?.approver ?? 'operator-ui';
  const reason = body?.reason ?? null;

  if (!approvalId || (action !== 'approve' && action !== 'reject')) {
    return NextResponse.json({ ok: false, error: 'invalid_request' }, { status: 400 });
  }

  const pool = getPgPool();
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    const existing = await client.query(
      `SELECT approval_id, staging_id, approval_status, approval_json
       FROM execution_approvals
       WHERE approval_id = $1
       LIMIT 1`,
      [approvalId],
    );

    if (existing.rowCount === 0) {
      await client.query('ROLLBACK');
      return NextResponse.json({ ok: false, error: 'approval_not_found' }, { status: 404 });
    }

    const row = existing.rows[0];
    const approvalStatus = action === 'approve' ? 'approved' : 'rejected';
    const stageStatus = action === 'approve' ? 'approved_for_execution' : 'rejected';
    const approvalJson = {
      ...(row.approval_json ?? {}),
      operator_action: action,
      operator_approver: approver,
      operator_reason: reason,
      operator_acted_at: new Date().toISOString(),
    };

    const updated = await client.query(
      `UPDATE execution_approvals
          SET approval_status = $2,
              approver = $3,
              approval_json = $4::jsonb
        WHERE approval_id = $1
      RETURNING approval_id, staging_id, approval_status, approver, approval_json, created_at`,
      [approvalId, approvalStatus, approver, JSON.stringify(approvalJson)],
    );

    await client.query(
      `UPDATE broker_order_staging
          SET stage_status = $2,
              stage_json = COALESCE(stage_json, '{}'::jsonb) || $3::jsonb
        WHERE staging_id = $1`,
      [
        row.staging_id,
        stageStatus,
        JSON.stringify({
          approval_id: approvalId,
          approval_status: approvalStatus,
          approval_action: action,
          approval_actor: approver,
          approval_reason: reason,
        }),
      ],
    );

    await client.query(
      `INSERT INTO broker_order_audit (audit_id, staging_id, audit_event, audit_json, created_at)
       VALUES ('audit_' || md5(random()::text || clock_timestamp()::text), $1, $2, $3::jsonb, now())`,
      [
        row.staging_id,
        `approval_${action}`,
        JSON.stringify({
          approval_id: approvalId,
          approval_status: approvalStatus,
          approver,
          reason,
        }),
      ],
    );

    await client.query('COMMIT');
    return NextResponse.json({ ok: true, row: updated.rows[0], stage_status: stageStatus });
  } catch (error) {
    await client.query('ROLLBACK');
    return NextResponse.json(
      { ok: false, error: error instanceof Error ? error.message : 'unknown_error' },
      { status: 500 },
    );
  } finally {
    client.release();
  }
}
