export class InMemoryRateLimiter {
  private readonly windows = new Map<string, { count: number; resetAt: number }>();

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
