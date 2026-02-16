import { mutation, query } from './_generated/server';
import { v } from 'convex/values';

export const getByUrl = query({
  args: { url: v.string() },
  handler: async (ctx, args) => {
    return await ctx.db
      .query('articles')
      .withIndex('by_url', (q) => q.eq('url', args.url))
      .unique();
  },
});

export const upsertMeta = mutation({
  args: {
    url: v.string(),
    source: v.string(),
    title: v.string(),
    publishedAt: v.optional(v.union(v.string(), v.null())),
    lang: v.optional(v.union(v.string(), v.null())),
    wordCount: v.optional(v.union(v.number(), v.null())),
    textPreview: v.optional(v.string()),
    textFileId: v.optional(v.id('_storage')),
    textSha256: v.optional(v.string()),
  },
  handler: async (ctx, args) => {
    const now = Date.now();
    const existing = await ctx.db
      .query('articles')
      .withIndex('by_url', (q) => q.eq('url', args.url))
      .unique();

    const patch = {
      source: args.source,
      title: args.title,
      publishedAt: args.publishedAt ?? undefined,
      lang: args.lang ?? undefined,
      wordCount: args.wordCount ?? undefined,
      textPreview: args.textPreview,
      textFileId: args.textFileId,
      textSha256: args.textSha256,
      ingestedAt: now,
    };

    if (!existing) {
      await ctx.db.insert('articles', {
        url: args.url,
        ...patch,
      });
      return { ok: true, inserted: true };
    }

    await ctx.db.patch(existing._id, patch);
    return { ok: true, updated: true };
  },
});
