import { query, mutation } from './_generated/server';
import { v } from 'convex/values';

const tf = v.union(v.literal('1d'), v.literal('1h'), v.literal('15m'));

export const latest = query({
  args: {
    ticker: v.string(),
    tf,
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.min(Math.max(args.limit ?? 500, 10), 5000);
    const rows = await ctx.db
      .query('candles')
      .withIndex('by_ticker_tf', (q) => q.eq('ticker', args.ticker).eq('tf', args.tf))
      .order('desc')
      .take(limit);

    // return ascending for chart
    return rows
      .sort((a, b) => a.ts - b.ts)
      .map((r) => ({
        timestamp: r.ts,
        open: r.o,
        high: r.h,
        low: r.l,
        close: r.c,
        volume: r.v ?? undefined,
      }));
  },
});

export const before = query({
  args: {
    ticker: v.string(),
    tf,
    beforeTs: v.number(),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.min(Math.max(args.limit ?? 500, 10), 5000);
    const rows = await ctx.db
      .query('candles')
      .withIndex('by_ticker_tf_ts', (q) =>
        q.eq('ticker', args.ticker).eq('tf', args.tf).lt('ts', args.beforeTs)
      )
      .order('desc')
      .take(limit);

    return rows
      .sort((a, b) => a.ts - b.ts)
      .map((r) => ({
        timestamp: r.ts,
        open: r.o,
        high: r.h,
        low: r.l,
        close: r.c,
        volume: r.v ?? undefined,
      }));
  },
});

// NOTE: candles ingestion is moving to TimescaleDB + History API.
// Convex candles are now considered optional/legacy; leave this for future cache use.
// Idempotent upsert by (ticker, tf, ts)
export const upsertMany = mutation({
  args: {
    ticker: v.string(),
    tf,
    candles: v.array(
      v.object({
        ts: v.number(),
        o: v.number(),
        h: v.number(),
        l: v.number(),
        c: v.number(),
        v: v.optional(v.number()),
        source: v.optional(v.string()),
      })
    ),
  },
  handler: async (ctx, args) => {
    const now = Date.now();

    // Simple approach: for each candle, check existing by index and patch/insert.
    // This is not the fastest possible (we can batch optimize later), but it's safe + correct.
    let inserted = 0;
    let updated = 0;

    for (const k of args.candles) {
      const existing = await ctx.db
        .query('candles')
        .withIndex('by_ticker_tf_ts', (q) =>
          q.eq('ticker', args.ticker).eq('tf', args.tf).eq('ts', k.ts)
        )
        .unique();

      const doc = {
        ticker: args.ticker,
        tf: args.tf,
        ts: k.ts,
        o: k.o,
        h: k.h,
        l: k.l,
        c: k.c,
        v: k.v,
        source: k.source,
        ingestedAt: now,
      } as const;

      if (!existing) {
        await ctx.db.insert('candles', doc);
        inserted += 1;
      } else {
        await ctx.db.patch(existing._id, doc);
        updated += 1;
      }
    }

    return { inserted, updated };
  },
});
