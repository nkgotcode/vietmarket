import Link from 'next/link';

export default function HomePage() {
  return (
    <main style={{ maxWidth: 980, margin: '40px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ marginBottom: 8 }}>vietstock-market</h1>
      <p style={{ color: '#555', marginTop: 0 }}>
        Private-by-login market intel: Vietstock news + ticker/company context.
      </p>

      <div style={{ display: 'flex', gap: 12, marginTop: 18, flexWrap: 'wrap' }}>
        <Link href="/app" style={{ padding: '10px 14px', border: '1px solid #ddd', borderRadius: 10 }}>
          Open app
        </Link>
        <Link href="/sign-in" style={{ padding: '10px 14px', border: '1px solid #ddd', borderRadius: 10 }}>
          Sign in
        </Link>
        <Link href="/sign-up" style={{ padding: '10px 14px', border: '1px solid #ddd', borderRadius: 10 }}>
          Sign up
        </Link>
      </div>

      <p style={{ color: '#777', marginTop: 22, fontSize: 14 }}>
        Domain: <code>vs.mydomain.com</code>
      </p>
    </main>
  );
}
