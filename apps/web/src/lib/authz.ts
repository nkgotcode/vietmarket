import 'server-only';

import { NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

import { isE2EBypass } from '@/lib/e2eBypass';

export async function requireAppAuth(req: Request): Promise<NextResponse | null> {
  const { userId } = await auth();
  if (userId || isE2EBypass(req)) return null;
  return NextResponse.json({ ok: false, error: 'unauthorized' }, { status: 401 });
}