import Link from 'next/link';
import AuthWidget from '../AuthWidget';
import ScreenerClient from './ScreenerClient';

export default function ScreenerPage() {
  return (
    <main style={{ maxWidth: 1200, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <div>
          <Link href="/app">← Back</Link>
          <div style={{ height: 8 }} />
        </div>
        <AuthWidget />
      </div>

      <ScreenerClient />
    </main>
  );
}
