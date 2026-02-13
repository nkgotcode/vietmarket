import { setTimeout as sleep } from 'node:timers/promises';

export async function fetchJsonWithRetry(url, {
  timeoutMs = 15000,
  retries = 3,
  backoffMs = 500,
  headers = {},
} = {}) {
  let lastErr;

  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
      const res = await fetch(url, {
        method: 'GET',
        headers: {
          accept: 'application/json',
          'content-type': 'application/json',
          ...headers,
        },
        signal: controller.signal,
      });

      let body;
      try {
        body = await res.json();
      } catch {
        body = null;
      }

      return {
        ok: res.ok,
        status: res.status,
        url,
        body,
      };
    } catch (err) {
      lastErr = err;
      if (attempt < retries) {
        await sleep(backoffMs * Math.pow(2, attempt));
      }
    } finally {
      clearTimeout(timer);
    }
  }

  throw lastErr;
}
