'use client';

import { useEffect, useState } from 'react';
import DeliveryEventsTable from '@/components/execution/DeliveryEventsTable';

type DeliveryRow = {
  delivery_id: string;
  delivery_kind: string;
  channel: string;
  delivery_status: string;
  target_ref: string | null;
  created_at: string;
};

type DeliveryPayload = {
  ok: boolean;
  rows: DeliveryRow[];
};

export default function DeliveryPage() {
  const [data, setData] = useState<DeliveryPayload | null>(null);
  useEffect(() => {
    fetch('/api/brain/delivery', { cache: 'no-store' }).then((r) => r.json() as Promise<DeliveryPayload>).then(setData);
  }, []);

  return (
    <main style={{ maxWidth: 1200, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ marginTop: 0 }}>Delivery events</h1>
      {!data ? <p>Loading delivery ledger…</p> : <DeliveryEventsTable rows={data.rows} />}
    </main>
  );
}
