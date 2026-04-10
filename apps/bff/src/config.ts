export const config = {
  appEnv: process.env.APP_ENV ?? "development",
  host: process.env.BFF_HOST ?? "0.0.0.0",
  port: Number(process.env.BFF_PORT ?? 8081),
  wsHeartbeatMs: Number(process.env.BFF_WS_HEARTBEAT_MS ?? 15000),
  manifestCacheTtlMs: Number(process.env.BFF_MANIFEST_CACHE_TTL_MS ?? 30000),
  rateLimitPerMinute: Number(process.env.BFF_RATE_LIMIT_PER_MINUTE ?? 120),
  redisUrl: process.env.REDIS_URL ?? "redis://localhost:6379/0",  // BL-008
  rateLimiterPrefix: process.env.BFF_RL_PREFIX ?? "bff:rl",       // BL-008
  auth: {
    issuer: process.env.BFF_AUTH_ISSUER ?? "",
    audience: process.env.BFF_AUTH_AUDIENCE ?? "",
    jwksUrl: process.env.BFF_AUTH_JWKS_URL ?? "",
    enforceInDevelopment: (process.env.BFF_AUTH_ENFORCE_IN_DEV ?? "false").toLowerCase() === "true"
  },
  policy: {
    defaultReleasabilityTag: process.env.BFF_POLICY_DEFAULT_RELEASABILITY ?? "NATO"
  },
  provider: {
    teleGeographyToken: process.env.TELEGEOGRAPHY_TOKEN ?? "",
    eoProviderToken: process.env.EO_PROVIDER_TOKEN ?? ""
  }
};
