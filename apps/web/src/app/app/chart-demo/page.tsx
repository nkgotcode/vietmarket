'use client';

import React, { useEffect, useRef } from 'react';
import { init, dispose, type KLineData } from 'klinecharts';

function makeLoader(data: KLineData[]) {
  let done = false;
  return {
    getBars: ({ type, callback }: { type: string; callback: (d: KLineData[], more?: boolean) => void }) => {
      if (type === 'init' && !done) {
        done = true;
        callback(data, true);
        return;
      }
      callback([], true);
    },
  };
}

const demoData: KLineData[] = [
  // timestamp in ms
  { timestamp: 1700000000000, open: 10, high: 11, low: 9.5, close: 10.4, volume: 12000 },
  { timestamp: 1700086400000, open: 10.4, high: 10.9, low: 10.2, close: 10.7, volume: 9000 },
  { timestamp: 1700172800000, open: 10.7, high: 11.2, low: 10.6, close: 10.9, volume: 14000 },
  { timestamp: 1700259200000, open: 10.9, high: 11.4, low: 10.8, close: 11.1, volume: 15000 },
];

export default function ChartDemoPage() {
  const elRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const el = elRef.current;
    if (!el) return;

    const chart = init(el);
    if (!chart) return;

    // KLineCharts v10 uses a dataLoader pattern.
    chart.setDataLoader(makeLoader(demoData));

    const onResize = () => chart.resize();
    window.addEventListener('resize', onResize);
    return () => {
      window.removeEventListener('resize', onResize);
      dispose(el);
    };
  }, []);

  return (
    <main style={{ maxWidth: 1100, margin: '24px auto', padding: 24, fontFamily: 'system-ui' }}>
      <h1 style={{ marginTop: 0 }}>KLineChart demo</h1>
      <p style={{ color: '#666' }}>This is a placeholder. Next step: load OHLCV from Convex.</p>
      <div
        ref={elRef}
        style={{ height: 520, border: '1px solid #ddd', borderRadius: 12, overflow: 'hidden' }}
      />
    </main>
  );
}
