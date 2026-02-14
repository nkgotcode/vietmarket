'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { init, dispose, type KLineData } from 'klinecharts';
import { useQuery, useMutation } from 'convex/react';
import { api } from '@convex/_generated/api';

type TF = '1d' | '1h' | '15m';

function tfLabel(tf: TF) {
  if (tf === '1d') return '1D';
  if (tf === '1h') return '1H';
  return '15m';
}

export default function ChartClient({ ticker }: { ticker: string }) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<ReturnType<typeof init> | null>(null);

  const [tf, setTf] = useState<TF>('1d');

  const data = useQuery(api.candles.latest, { ticker, tf, limit: 800 });
  const loadBefore = useQuery(
    api.candles.before,
    data && data.length ? { ticker, tf, beforeTs: data[0].timestamp, limit: 800 } : 'skip'
  );

  // For later: local ingest worker will call upsertMany, not the browser.
  // Keeping mutation import as a placeholder for dev manual testing.
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const upsertMany = useMutation(api.candles.upsertMany);

  const klineData: KLineData[] | null = useMemo(() => {
    if (!data) return null;
    return data.map((d) => ({
      timestamp: d.timestamp,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
      volume: d.volume,
    }));
  }, [data]);

  useEffect(() => {
    const el = elRef.current;
    if (!el) return;

    const chart = init(el);
    if (!chart) return;
    chartRef.current = chart;

    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      dispose(el);
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    chart.resetData();
  }, [tf]);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;
    if (!klineData) return;

    // Feed data via a simple dataLoader. (We can later wire scroll-left/backfill properly.)
    let usedInit = false;
    const initData = klineData;
    const beforeData = (loadBefore || []) as KLineData[];

    chart.setDataLoader({
      getBars: ({ type, callback }) => {
        if (type === 'init' && !usedInit) {
          usedInit = true;
          callback(initData, true);
          return;
        }
        if (type === 'backward') {
          // NOTE: this is naive; klinecharts gives us a timestamp to page from.
          // We'll switch to action-driven paging once we hook scroll events.
          callback(beforeData, true);
          return;
        }
        callback([], true);
      },
    });
  }, [klineData, loadBefore]);

  return (
    <div>
      <div style={{ display: 'flex', gap: 10, alignItems: 'center', margin: '10px 0 12px' }}>
        <div style={{ fontWeight: 600 }}>Timeframe</div>
        {(['15m', '1h', '1d'] as TF[]).map((t) => (
          <button
            key={t}
            onClick={() => setTf(t)}
            style={{
              padding: '6px 10px',
              borderRadius: 10,
              border: '1px solid #ddd',
              background: t === tf ? '#111' : 'white',
              color: t === tf ? 'white' : '#111',
              cursor: 'pointer',
            }}
          >
            {tfLabel(t)}
          </button>
        ))}
      </div>

      <div style={{ height: 560, border: '1px solid #ddd', borderRadius: 12, overflow: 'hidden' }} ref={elRef} />

      <div style={{ color: '#666', marginTop: 10, fontSize: 13 }}>
        Loaded: {data ? data.length : '…'} bars ({tfLabel(tf)}). If you see 0, we haven’t backfilled candles into Convex yet.
      </div>
    </div>
  );
}
