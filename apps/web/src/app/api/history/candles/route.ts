import { NextResponse } from 'next/server';
import { auth } from '@clerk/nextjs/server';

export async function GET(req: Request) {
  const { userId } = await auth();
  if (!userId) {
    return NextResponse.json({ ok: false, error: 'unauthorized' }, { status: 401 });
  }

  const baseUrl = process.env.HISTORY_API_URL;
  const apiKey = process.env.HISTORY_API_KEY;
  if (!baseUrl || !apiKey) {
    return NextResponse.json(
      { ok: false, error: 'server_misconfigured' },
      { status: 500 }
    );
  }

  const url = new URL(req.url);
  const ticker = url.searchParams.get('ticker') || '';
  const tf = url.searchParams.get('tf') || '';
  const beforeTs = url.searchParams.get('beforeTs');
  const limit = url.searchParams.get('limit');

  const upstream = new URL(baseUrl.replace(/\/$/, '') + '/candles');
  upstream.searchParams.set('ticker', ticker);
  upstream.searchParams.set('tf', tf);
  if (beforeTs) upstream.searchParams.set('beforeTs', beforeTs);
  if (limit) upstream.searchParams.set('limit', limit);

  const r = await fetch(upstream.toString(), {
    headers: {
      'x-api-key': apiKey,
    },
    cache: 'no-store',
  });

  const text = await r.text();
  return new NextResponse(text, {
    status: r.status,
    headers: {
      'content-type': r.headers.get('content-type') || 'application/json',
    },
  });
}
