import { defineSchema, defineTable } from 'convex/server';
import { v } from 'convex/values';

// Canonical VietMarket schema (Convex).
// Start with candles + minimal symbol/news primitives; expand incrementally.

export default defineSchema({
  candles: defineTable({
    ticker: v.string(),
    tf: v.union(v.literal('1d'), v.literal('1h'), v.literal('15m')),
    ts: v.number(), // unix ms
    o: v.number(),
    h: v.number(),
    l: v.number(),
    c: v.number(),
    v: v.optional(v.number()),
    // provenance
    source: v.optional(v.string()),
    ingestedAt: v.optional(v.number()),
  })
    .index('by_ticker_tf_ts', ['ticker', 'tf', 'ts'])
    .index('by_ticker_tf', ['ticker', 'tf']),

  symbols: defineTable({
    ticker: v.string(),
    name: v.optional(v.string()),
    exchange: v.optional(v.string()),
    active: v.optional(v.boolean()),
    updatedAt: v.optional(v.number()),
  }).index('by_ticker', ['ticker']),

  articles: defineTable({
    url: v.string(),
    source: v.string(),
    title: v.string(),
    publishedAt: v.optional(v.string()),
    wordCount: v.optional(v.number()),
    lang: v.optional(v.string()),

    // text handling
    textPreview: v.optional(v.string()),
    textFileId: v.optional(v.id('_storage')),
    textSha256: v.optional(v.string()),

    ingestedAt: v.optional(v.number()),
  }).index('by_url', ['url']),

  articleSymbols: defineTable({
    articleUrl: v.string(),
    ticker: v.string(),
    confidence: v.optional(v.number()),
    method: v.optional(v.string()),
  })
    .index('by_ticker', ['ticker'])
    .index('by_article', ['articleUrl']),

  fiLatest: defineTable({
    ticker: v.string(),
    period: v.string(),
    statement: v.string(),
    periodDate: v.optional(v.string()),
    metric: v.string(),
    value: v.optional(v.number()),
    fetchedAt: v.optional(v.string()),
    ingestedAt: v.optional(v.number()),
  })
    .index('by_ticker', ['ticker'])
    .index('by_ticker_metric', ['ticker', 'metric']),

  // Repair queue: gap detector enqueues work; worker marks done.
  // Shard leases: coordinate HA workers across nodes.
  shardLeases: defineTable({
    job: v.string(),
    shard: v.number(),
    ownerId: v.string(),
    leaseUntilMs: v.number(),
    lastProgressAtMs: v.number(),
    meta: v.optional(v.string()),
    updatedAt: v.number(),
  })
    .index('by_job_shard', ['job', 'shard'])
    .index('by_job_owner', ['job', 'ownerId'])
    .index('by_lease_until', ['leaseUntilMs']),

  candleRepairQueue: defineTable({
    ticker: v.string(),
    tf: v.union(v.literal('1d'), v.literal('1h'), v.literal('15m')),
    windowStartTs: v.number(),
    windowEndTs: v.number(),
    expectedBars: v.number(),
    note: v.optional(v.string()),

    status: v.union(v.literal('queued'), v.literal('running'), v.literal('done'), v.literal('error')),
    attempts: v.number(),
    lastError: v.optional(v.string()),

    createdAt: v.number(),
    updatedAt: v.number(),
  })
    .index('by_status_created', ['status', 'createdAt'])
    .index('by_ticker_tf_window', ['ticker', 'tf', 'windowStartTs', 'windowEndTs']),

  // Audit log for self-heal runs.
  candleRepairs: defineTable({
    ticker: v.string(),
    tf: v.union(v.literal('1d'), v.literal('1h'), v.literal('15m')),
    windowStartTs: v.number(),
    windowEndTs: v.number(),
    missingCount: v.number(),
    note: v.optional(v.string()),
    createdAt: v.number(),
  })
    .index('by_ticker_tf_created', ['ticker', 'tf', 'createdAt']),
});
