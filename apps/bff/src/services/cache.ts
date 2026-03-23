type CacheEntry<T> = {
  value: T;
  expiresAt: number;
};

export class InMemoryCache {
  private readonly entries = new Map<string, CacheEntry<unknown>>();

  get<T>(key: string): T | null {
    const entry = this.entries.get(key);
    if (!entry) {
      return null;
    }
    if (entry.expiresAt < Date.now()) {
      this.entries.delete(key);
      return null;
    }
    return entry.value as T;
  }

  set<T>(key: string, value: T, ttlMs: number): void {
    this.entries.set(key, { value, expiresAt: Date.now() + ttlMs });
  }
}
