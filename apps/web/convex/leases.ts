import { mutation, query } from './_generated/server';
import { v } from 'convex/values';

// Default stale policy:
// - latest jobs: 10m
// - deep backfill jobs: 30m
// Caller passes staleMinutes explicitly.

function now() {
  return Date.now();
}

export const get = query({
  args: { job: v.string(), shard: v.number() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query('shardLeases')
      .withIndex('by_job_shard', (q) => q.eq('job', args.job).eq('shard', args.shard))
      .unique();
  },
});

export const tryClaim = mutation({
  args: {
    job: v.string(),
    shard: v.number(),
    ownerId: v.string(),
    leaseMs: v.optional(v.number()),
    staleMinutes: v.number(),
    meta: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const t = now();
    const leaseMs = Math.min(Math.max(args.leaseMs ?? 5 * 60_000, 30_000), 30 * 60_000);
    const staleMs = Math.max(1, args.staleMinutes) * 60_000;

    const row = await ctx.db
      .query('shardLeases')
      .withIndex('by_job_shard', (q) => q.eq('job', args.job).eq('shard', args.shard))
      .unique();

    // Claim if missing, expired, or stale.
    const canClaim =
      !row ||
      row.leaseUntilMs < t ||
      row.lastProgressAtMs < t - staleMs;

    if (!canClaim) {
      return { ok: false, ownerId: row!.ownerId, leaseUntilMs: row!.leaseUntilMs, lastProgressAtMs: row!.lastProgressAtMs };
    }

    const next = {
      job: args.job,
      shard: args.shard,
      ownerId: args.ownerId,
      leaseUntilMs: t + leaseMs,
      lastProgressAtMs: row?.lastProgressAtMs ?? t,
      meta: args.meta,
      updatedAt: t,
    };

    if (!row) {
      const id = await ctx.db.insert('shardLeases', next);
      return { ok: true, claimed: true, id, ...next };
    }

    await ctx.db.patch(row._id, next);
    return { ok: true, claimed: true, id: row._id, ...next };
  },
});

export const renew = mutation({
  args: {
    job: v.string(),
    shard: v.number(),
    ownerId: v.string(),
    leaseMs: v.optional(v.number()),
    meta: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const t = now();
    const leaseMs = Math.min(Math.max(args.leaseMs ?? 5 * 60_000, 30_000), 30 * 60_000);

    const row = await ctx.db
      .query('shardLeases')
      .withIndex('by_job_shard', (q) => q.eq('job', args.job).eq('shard', args.shard))
      .unique();

    if (!row) return { ok: false, reason: 'missing' };
    if (row.ownerId !== args.ownerId) return { ok: false, reason: 'not-owner', ownerId: row.ownerId };

    await ctx.db.patch(row._id, {
      leaseUntilMs: t + leaseMs,
      meta: args.meta ?? row.meta,
      updatedAt: t,
    });
    return { ok: true };
  },
});

export const reportProgress = mutation({
  args: {
    job: v.string(),
    shard: v.number(),
    ownerId: v.string(),
    meta: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const t = now();
    const row = await ctx.db
      .query('shardLeases')
      .withIndex('by_job_shard', (q) => q.eq('job', args.job).eq('shard', args.shard))
      .unique();

    if (!row) return { ok: false, reason: 'missing' };
    if (row.ownerId !== args.ownerId) return { ok: false, reason: 'not-owner', ownerId: row.ownerId };

    await ctx.db.patch(row._id, {
      lastProgressAtMs: t,
      meta: args.meta ?? row.meta,
      updatedAt: t,
    });
    return { ok: true };
  },
});
