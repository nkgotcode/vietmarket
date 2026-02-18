import { NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

export async function GET(req: Request) {
  const { userId } = await auth();
  if (!userId) return NextResponse.json({ ok: false, error: 'unauthorized' }, { status: 401 });

  const baseUrl = process.env.HISTORY_API_URL;
  const apiKey = process.env.HISTORY_API_KEY;
  if (!baseUrl || !apiKey) {
    return NextResponse.json({ ok: false, error: 'server_misconfigured' }, { status: 500 });
  }

  const url = new URL(req.url);
  const ticker = url.searchParams.get('ticker') || '';
  const limit = url.searchParams.get('limit');

  const upstream = new URL(baseUrl.replace(/\/$/, '') + '/news/by-ticker');
  upstream.searchParams.set('ticker', ticker);
  if (limit) upstream.searchParams.set('limit', limit);

  const r = await fetch(upstream.toString(), {
    headers: { 'x-api-key': apiKey },
    cache: 'no-store',
  });

  const text = await r.text();
  return new NextResponse(text, {
    status: r.status,
    headers: { 'content-type': r.headers.get('content-type') || 'application/json' },
  });
}
