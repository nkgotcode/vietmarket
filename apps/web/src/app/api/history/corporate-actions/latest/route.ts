import { NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

export async function GET(req: Request) {
  const { userId } = await auth();
  const bypass = (process.env.E2E_BYPASS_AUTH === '1') && (process.env.E2E_BYPASS_TOKEN) && (req.headers.get('x-e2e-bypass') === process.env.E2E_BYPASS_TOKEN);
  if (!userId && !bypass) return NextResponse.json({ ok: false, error: 'unauthorized' }, { status: 401 });

  const baseUrl = process.env.HISTORY_API_URL;
  const apiKey = process.env.HISTORY_API_KEY;
  if (!baseUrl || !apiKey) return NextResponse.json({ ok: false, error: 'server_misconfigured' }, { status: 500 });

  const url = new URL(req.url);
  const limit = url.searchParams.get('limit');
  const beforeExDate = url.searchParams.get('beforeExDate');
  const beforeId = url.searchParams.get('beforeId');

  const upstream = new URL(baseUrl.replace(/\/$/, '') + '/corporate-actions/latest');
  if (limit) upstream.searchParams.set('limit', limit);
  if (beforeExDate) upstream.searchParams.set('beforeExDate', beforeExDate);
  if (beforeId) upstream.searchParams.set('beforeId', beforeId);

  const r = await fetch(upstream.toString(), { headers: { 'x-api-key': apiKey }, cache: 'no-store' });
  const text = await r.text();
  return new NextResponse(text, { status: r.status, headers: { 'content-type': r.headers.get('content-type') || 'application/json' } });
}
