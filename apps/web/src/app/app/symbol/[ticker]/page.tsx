import Link from 'next/link';
import ChartClient from './ChartClient';
import SymbolHeadlinesClient from './SymbolHeadlinesClient';
import FundamentalsClient from './FundamentalsClient';
import AuthWidget from '../../AuthWidget';

export default async function SymbolPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = await params;
  const t = ticker.toUpperCase();

  return (
    <main style={{ maxWidth: 1200, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <div>
          <Link href="/app">← Back</Link>
          <h1 style={{ margin: '8px 0 0' }}>{t}</h1>
          <div style={{ color: '#666' }}>KLineChart backed by History API (TimescaleDB HA).</div>
        </div>
        <AuthWidget />
      </div>

      <div style={{ marginTop: 14 }}>
        <ChartClient ticker={t} />
      </div>

      <SymbolHeadlinesClient ticker={t} />
      <FundamentalsClient ticker={t} />
    </main>
  );
}
