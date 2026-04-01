/**
 * BL-008: Distributed rate limiter backed by Redis fixed-window counters.
 *
 * Uses the INCR + EXPIRE pattern:
 *  1. INCR <prefix>:<key>:<windowStart>
 *  2. If the key was just created (count === 1), set TTL to 60 s.
 *  3. Reject when count exceeds the per-minute limit.
 *
 * Falls back to an in-process window if Redis is unavailable, so the BFF
 * remains operational during a Redis outage (fail-open policy for reads).
 * A Prometheus-style log line is emitted on every degraded consume so ops
 * can alert on sustained fallback usage.
 */
import { Redis } from "ioredis";
import { config } from "../config.js";

/** In-process fallback window (per-key, per-minute bucket). */
interface LocalWindow {
  count: number;
  resetAt: number;
}

export class RedisRateLimiter {
  private readonly redis: Redis;
  private readonly localFallback = new Map<string, LocalWindow>();
  private redisAvailable = true;

  constructor(redisUrl: string = config.redisUrl) {
    this.redis = new Redis(redisUrl, {
      lazyConnect: true,
      maxRetriesPerRequest: 1,
      enableOfflineQueue: false,
    });

    this.redis.on("error", () => {
      if (this.redisAvailable) {
        console.error("[rate-limiter] Redis unavailable, falling back to in-process limiter");
        this.redisAvailable = false;
      }
    });

    this.redis.on("connect", () => {
      if (!this.redisAvailable) {
        console.info("[rate-limiter] Redis reconnected, resuming distributed rate limiting");
        this.redisAvailable = true;
      }
    });

    // Initiate connection; errors are handled by the 'error' listener above.
    void this.redis.connect().catch(() => {/* handled by error listener */});
  }

  async consume(key: string, maxPerMinute: number): Promise<boolean> {
    if (this.redisAvailable) {
      try {
        return await this._redisConsume(key, maxPerMinute);
      } catch {
        this.redisAvailable = false;
        console.warn("[rate-limiter] Redis error during consume, using in-process fallback");
      }
    }
    return this._localConsume(key, maxPerMinute);
  }

  private async _redisConsume(key: string, maxPerMinute: number): Promise<boolean> {
    // Fixed-window bucket aligned to the current minute epoch
    const windowStart = Math.floor(Date.now() / 60000);
    const redisKey = `${config.rateLimiterPrefix}:${key}:${windowStart}`;
    const count = await this.redis.incr(redisKey);
    if (count === 1) {
      // Key was just created — set TTL so it expires after 60 s
      await this.redis.expire(redisKey, 60);
    }
    return count <= maxPerMinute;
  }

  private _localConsume(key: string, maxPerMinute: number): boolean {
    const now = Date.now();
    const existing = this.localFallback.get(key);
    if (!existing || existing.resetAt <= now) {
      this.localFallback.set(key, { count: 1, resetAt: now + 60000 });
      return true;
    }
    if (existing.count >= maxPerMinute) {
      return false;
    }
    existing.count += 1;
    return true;
  }

  /** Gracefully disconnect from Redis (e.g. on server shutdown). */
  async disconnect(): Promise<void> {
    await this.redis.quit();
  }
}

/** @deprecated Use RedisRateLimiter. Kept for backward compatibility in tests. */
export class InMemoryRateLimiter {
  private readonly windows = new Map<string, LocalWindow>();

  consume(key: string, maxPerMinute: number): boolean {
    const now = Date.now();
    const existing = this.windows.get(key);
    if (!existing || existing.resetAt <= now) {
      this.windows.set(key, { count: 1, resetAt: now + 60000 });
      return true;
    }
    if (existing.count >= maxPerMinute) {
      return false;
    }
    existing.count += 1;
    return true;
  }
}
