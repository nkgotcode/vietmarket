import { NextResponse } from 'next/server';

import { requireAppAuth } from '@/lib/authz';
import { getPgPool } from '@/lib/pg';

export async function GET(req: Request) {
  const denied = await requireAppAuth(req);
  if (denied) return denied;

  const pool = getPgPool();
  const runs = await pool.query(
    `SELECT run_id, job_name, dataset_name, nomad_job_id, nomad_alloc_id, node_name,
            started_at, finished_at, status, rows_read, rows_written, rows_upserted,
            warnings_count, errors_count, summary_json, created_at
       FROM worker_runs
      ORDER BY started_at DESC
      LIMIT 50`
  );
  const failures = await pool.query(
    `SELECT failure_id, run_id, job_name, stage, error_class, error_hash, error_message, retryable, created_at
       FROM worker_failures
      ORDER BY created_at DESC
      LIMIT 50`
  );

  return NextResponse.json({ ok: true, runs: runs.rows, failures: failures.rows });
}