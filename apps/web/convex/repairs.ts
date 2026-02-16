import { mutation } from './_generated/server';
import { v } from 'convex/values';

export const logCandleRepair = mutation({
  args: {
    ticker: v.string(),
    tf: v.union(v.literal('1d'), v.literal('1h'), v.literal('15m')),
    windowStartTs: v.number(),
    windowEndTs: v.number(),
    missingCount: v.number(),
    note: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const now = Date.now();
    const id = await ctx.db.insert('candleRepairs', {
      ...args,
      createdAt: now,
    });
    return { id };
  },
});
