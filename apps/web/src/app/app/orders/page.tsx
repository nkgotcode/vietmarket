'use client';

import { useEffect, useState } from 'react';
import PolicyResultPanel from '@/components/portfolio/PolicyResultPanel';

type OrdersPayload = {
  ok: boolean;
  intents: Array<Record<string, unknown>>;
  orders: Array<Record<string, unknown>>;
  fills: Array<Record<string, unknown>>;
};

type PolicyPayload = {
  ok: boolean;
  rows: Array<{
    ticker: string;
    overall_result: string;
    blocking_flag: boolean;
    checks_json?: Array<{ check_name: string; passed: boolean; blocking: boolean; detail: unknown }> | null;
  }>;
};

export default function OrdersPage() {
  const [orders, setOrders] = useState<OrdersPayload | null>(null);
  const [policy, setPolicy] = useState<PolicyPayload | null>(null);
  useEffect(() => {
    Promise.all([
      fetch('/api/brain/orders', { cache: 'no-store' }).then((r)=>r.json() as Promise<OrdersPayload>),
      fetch('/api/brain/policy', { cache: 'no-store' }).then((r)=>r.json() as Promise<PolicyPayload>),
    ]).then(([o,p]) => { setOrders(o); setPolicy(p); });
  }, []);
  return (
    <main style={{ maxWidth: 1200, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ marginTop: 0 }}>Orders</h1>
      {!orders || !policy ? <p>Loading orders…</p> : <section style={{ display: 'grid', gap: 16 }}>
        <pre style={{ margin:0, padding:12, borderRadius:8, background:'#fafafa', overflowX:'auto', fontSize:12 }}>{JSON.stringify(orders, null, 2)}</pre>
        <h3>Policy results</h3>
        <PolicyResultPanel rows={policy.rows} />
      </section>}
    </main>
  );
}
