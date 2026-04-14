import 'server-only';

import { Pool } from 'pg';

const connectionString = process.env.PG_URL || process.env.DATABASE_URL;

let pool: Pool | null = null;

export function getPgPool(): Pool {
  if (!connectionString) {
    throw new Error('Missing PG_URL or DATABASE_URL');
  }

  if (!pool) {
    pool = new Pool({ connectionString });
  }

  return pool;
}