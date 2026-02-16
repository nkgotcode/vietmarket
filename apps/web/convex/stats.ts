import { query } from './_generated/server';
import { v } from 'convex/values';

const tf = v.union(v.literal('1d'), v.literal('1h'), v.literal('15m'));

export const candlesLatestTs = query({
  args: { ticker: v.string(), tf },
  handler: async (ctx, args) => {
    const row = await ctx.db
      .query('candles')
      .withIndex('by_ticker_tf', (q) => q.eq('ticker', args.ticker).eq('tf', args.tf))
      .order('desc')
      .first();
    return row ? { ts: row.ts } : null;
  },
});

export const repairQueueCounts = query({
  args: {},
  handler: async (ctx) => {
    const statuses = ['queued', 'running', 'done', 'error'] as const;
    const out: Record<string, number> = {};
    for (const s of statuses) {
      const n = (await ctx.db
        .query('candleRepairQueue')
        .withIndex('by_status_created', (q) => q.eq('status', s))
        .collect()).length;
      out[s] = n;
    }
    return out;
  },
});
