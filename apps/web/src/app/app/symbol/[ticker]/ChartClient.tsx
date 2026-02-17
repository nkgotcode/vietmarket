'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { init, dispose, type KLineData } from 'klinecharts';
import { fetchCandles, type TF } from '@/lib/historyApi';

function tfLabel(tf: TF) {
  if (tf === '1d') return '1D';
  if (tf === '1h') return '1H';
  return '15m';
}

function toKline(rows: { ts: number; o: number | null; h: number | null; l: number | null; c: number | null; v: number | null }[]): KLineData[] {
  return rows
    .filter((r) => r.ts != null && r.o != null && r.h != null && r.l != null && r.c != null)
    .map((r) => ({
      timestamp: r.ts,
      open: r.o as number,
      high: r.h as number,
      low: r.l as number,
      close: r.c as number,
      volume: r.v ?? undefined,
    }));
}

export default function ChartClient({ ticker }: { ticker: string }) {
  const elRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<ReturnType<typeof init> | null>(null);

  const [tf, setTf] = useState<TF>('1d');
  const [initRows, setInitRows] = useState<KLineData[] | null>(null);
  const [oldestTs, setOldestTs] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const label = useMemo(() => tfLabel(tf), [tf]);

  // Mount chart
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

  // Load initial window for timeframe
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr(null);
    setInitRows(null);
    setOldestTs(null);

    (async () => {
      try {
        const { rows } = await fetchCandles({ ticker, tf, limit: 800 });
        const k = toKline(rows);
        // API returns newest-first; chart wants ascending
        k.sort((a, b) => a.timestamp - b.timestamp);

        if (cancelled) return;
        setInitRows(k);
        setOldestTs(k.length ? k[0].timestamp : null);
      } catch (e: any) {
        if (cancelled) return;
        setErr(String(e?.message || e));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [ticker, tf]);

  // Wire chart data loader
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    chart.resetData();

    let usedInit = false;
    let paging = false;

    chart.setDataLoader({
      getBars: async ({ type, callback }) => {
        try {
          if (type === 'init' && !usedInit) {
            usedInit = true;
            callback(initRows || [], true);
            return;
          }

          if (type === 'backward') {
            if (paging) {
              callback([], true);
              return;
            }
            if (!oldestTs) {
              callback([], true);
              return;
            }

            paging = true;
            const { rows } = await fetchCandles({ ticker, tf, beforeTs: oldestTs, limit: 800 });
            const k = toKline(rows);
            // chart expects ascending for appended batches too
            k.sort((a, b) => a.timestamp - b.timestamp);

            if (k.length) {
              setOldestTs(k[0].timestamp);
            }

            callback(k, true);
            paging = false;
            return;
          }

          callback([], true);
        } catch {
          paging = false;
          callback([], true);
        }
      },
    });
  }, [initRows, oldestTs, ticker, tf]);

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
        {loading ? 'Loading…' : `Loaded: ${initRows ? initRows.length : 0} bars (${label}).`}
        {err ? <div style={{ color: '#b00', marginTop: 6 }}>Error: {err}</div> : null}
      </div>
    </div>
  );
}
