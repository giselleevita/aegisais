import type { FastifyInstance } from "fastify";
import { config } from "../config.js";
import { authMiddleware } from "../middleware/auth.js";
import { requireClassification, requireReleasability } from "../middleware/policy.js";
import { LayerRegistryService } from "../services/layerRegistryService.js";
import { InMemoryCache } from "../services/cache.js";
import { InMemoryRateLimiter } from "../services/rateLimiter.js";

export async function registerLayerRoutes(app: FastifyInstance): Promise<void> {
  const layerRegistry = new LayerRegistryService();
  const cache = new InMemoryCache();
  const limiter = new InMemoryRateLimiter();

  app.get(
    "/v1/layers/manifest",
    {
      preHandler: [
        authMiddleware,
        requireClassification("CONFIDENTIAL"),
        requireReleasability(config.policy.defaultReleasabilityTag),
      ],
    },
    async (request, reply) => {
    const identity = request.viewer?.userId ?? request.ip;
    if (!limiter.consume(`manifest:${identity}`, config.rateLimitPerMinute)) {
      return reply.code(429).send({ error: "Rate limit exceeded" });
    }

    const cached = cache.get<unknown>("layers:manifest");
    if (cached) {
      return reply.send(cached);
    }

    const allLayers = await layerRegistry.listLayers();
    const licensed = allLayers.filter((layer) =>
      (request.viewer?.licenses ?? []).includes(layer.licensedFeature)
    );
    const payload = { layers: licensed, generatedAt: new Date().toISOString() };
    cache.set("layers:manifest", payload, config.manifestCacheTtlMs);
    return reply.send(payload);
    }
  );
}
