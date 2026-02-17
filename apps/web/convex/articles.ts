import { action, query } from './_generated/server';
import { v } from 'convex/values';
import { api } from './_generated/api';

function sha256Hex(input: Uint8Array): Promise<string> {
  // crypto.subtle expects BufferSource; ensure ArrayBuffer, not a SharedArrayBuffer-like.
  // Copy into a fresh ArrayBuffer (avoids SharedArrayBuffer typing issues in some TS/libdom combos)
  const ab = new ArrayBuffer(input.byteLength);
  new Uint8Array(ab).set(input);
  return crypto.subtle.digest('SHA-256', ab).then((buf) => {
    const bytes = new Uint8Array(buf);
    return Array.from(bytes)
      .map((b) => b.toString(16).padStart(2, '0'))
      .join('');
  });
}

export const upsertWithText = action({
  args: {
    url: v.string(),
    source: v.string(),
    title: v.string(),
    publishedAt: v.optional(v.union(v.string(), v.null())),
    lang: v.optional(v.union(v.string(), v.null())),
    wordCount: v.optional(v.union(v.number(), v.null())),
    text: v.string(),
  },
  handler: async (ctx, args) => {
    const now = Date.now();
    const enc = new TextEncoder();
    const bytes = enc.encode(args.text);
    const textSha256 = await sha256Hex(bytes);

    const preview = args.text.slice(0, 5000);

    const existing = await ctx.runQuery(api.articlesMeta.getByUrl, { url: args.url });

    // If text is unchanged, just ensure metadata exists.
    if (existing && existing.textSha256 === textSha256) {
      await ctx.runMutation(api.articlesMeta.upsertMeta, {
        url: args.url,
        source: args.source,
        title: args.title,
        publishedAt: args.publishedAt ?? undefined,
        lang: args.lang ?? undefined,
        wordCount: args.wordCount ?? undefined,
        textPreview: preview,
        textFileId: existing.textFileId ?? undefined,
        textSha256,
      });
      return { ok: true, updated: true, stored: false, url: args.url };
    }

    // Store as a file in Convex storage.
    const blob = new Blob([bytes], { type: 'text/plain; charset=utf-8' });
    const fileId = await ctx.storage.store(blob);

    await ctx.runMutation(api.articlesMeta.upsertMeta, {
      url: args.url,
      source: args.source,
      title: args.title,
      publishedAt: args.publishedAt ?? undefined,
      lang: args.lang ?? undefined,
      wordCount: args.wordCount ?? undefined,
      textPreview: preview,
      textFileId: fileId,
      textSha256,
    });

    return { ok: true, updated: true, stored: true, url: args.url };
  },
});

export const getTextUrl = query({
  args: { url: v.string() },
  handler: async (ctx, args) => {
    const row = await ctx.db
      .query('articles')
      .withIndex('by_url', (q) => q.eq('url', args.url))
      .unique();
    if (!row?.textFileId) return null;
    return await ctx.storage.getUrl(row.textFileId);
  },
});
