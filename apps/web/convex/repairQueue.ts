import { mutation, query } from './_generated/server';
import { v } from 'convex/values';

const tf = v.union(v.literal('1d'), v.literal('1h'), v.literal('15m'));

export const enqueue = mutation({
  args: {
    ticker: v.string(),
    tf,
    windowStartTs: v.number(),
    windowEndTs: v.number(),
    expectedBars: v.number(),
    note: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const now = Date.now();

    // Deduplicate by window.
    const existing = await ctx.db
      .query('candleRepairQueue')
      .withIndex('by_ticker_tf_window', (q) =>
        q
          .eq('ticker', args.ticker)
          .eq('tf', args.tf)
          .eq('windowStartTs', args.windowStartTs)
          .eq('windowEndTs', args.windowEndTs)
      )
      .unique();

    if (existing) {
      if (existing.status === 'done') {
        // Allow re-queue by creating a new record? For now, keep done.
        return { id: existing._id, deduped: true, status: existing.status };
      }
      await ctx.db.patch(existing._id, {
        expectedBars: args.expectedBars,
        note: args.note,
        updatedAt: now,
      });
      return { id: existing._id, deduped: true, status: existing.status };
    }

    const id = await ctx.db.insert('candleRepairQueue', {
      ...args,
      status: 'queued',
      attempts: 0,
      createdAt: now,
      updatedAt: now,
    });
    return { id, deduped: false, status: 'queued' };
  },
});

export const nextQueued = query({
  args: {
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = Math.min(Math.max(args.limit ?? 10, 1), 50);
    const rows = await ctx.db
      .query('candleRepairQueue')
      .withIndex('by_status_created', (q) => q.eq('status', 'queued'))
      .order('asc')
      .take(limit);
    return rows;
  },
});

export const markRunning = mutation({
  args: {
    id: v.id('candleRepairQueue'),
  },
  handler: async (ctx, args) => {
    const now = Date.now();
    const row = await ctx.db.get(args.id);
    if (!row) throw new Error('not found');
    if (row.status !== 'queued') return { ok: false, status: row.status };
    await ctx.db.patch(args.id, {
      status: 'running',
      attempts: row.attempts + 1,
      updatedAt: now,
    });
    return { ok: true };
  },
});

export const markDone = mutation({
  args: {
    id: v.id('candleRepairQueue'),
  },
  handler: async (ctx, args) => {
    const now = Date.now();
    await ctx.db.patch(args.id, { status: 'done', updatedAt: now, lastError: undefined });
    return { ok: true };
  },
});

export const markError = mutation({
  args: {
    id: v.id('candleRepairQueue'),
    error: v.string(),
  },
  handler: async (ctx, args) => {
    const now = Date.now();
    await ctx.db.patch(args.id, { status: 'error', updatedAt: now, lastError: args.error.slice(0, 400) });
    return { ok: true };
  },
});
