import type { FastifyInstance, FastifyRequest } from "fastify";
import { config } from "../config.js";
import { authMiddleware } from "../middleware/auth.js";
import { requireClassification, requireReleasability } from "../middleware/policy.js";
import { requireLicense } from "../middleware/licensing.js";
import { LayerRegistryService } from "../services/layerRegistryService.js";

interface QueryBody {
  layerIds: string[];
  bbox?: [number, number, number, number];
  timeRange?: { start?: string; end?: string };
  limit?: number;
}

function authorization(request: FastifyRequest): string {
  return request.headers.authorization ?? "";
}

async function upstream<T>(request: FastifyRequest, path: string): Promise<T> {
  const response = await fetch(`${config.upstreamApiUrl}${path}`, {
    headers: { Authorization: authorization(request) }
  });
  if (!response.ok) {
    throw new Error(`upstream_${response.status}`);
  }
  return response.json() as Promise<T>;
}

const policy = [
  authMiddleware,
  requireClassification("CONFIDENTIAL"),
  requireReleasability(config.policy.defaultReleasabilityTag),
];

export async function registerCanonicalRoutes(app: FastifyInstance): Promise<void> {
  app.get("/v1/layers", { preHandler: policy }, async (request) => {
    const layers = (await new LayerRegistryService().listLayers()).filter((layer) =>
      (request.viewer?.licenses ?? []).includes(layer.licensedFeature)
    );
    return {
      layers: layers.map((layer) => ({
        id: layer.id,
        name: layer.name,
        description: `${layer.source} (${layer.mode ?? "reference"})`,
        geometryType: layer.id.includes("fusion") ? "Point/Event" : "Point",
        entityType: layer.domain === "maritime" ? "vessel" : layer.domain,
        queryable: true,
        streamable: layer.mode === "live" || layer.mode === "derived",
        confidence: { score: layer.mode === "historical_replay" ? 0.8 : 0.9, method: layer.confidenceMethod ?? "source_metadata" },
        provenance: { source: layer.source, processor: "aegisais-bff-layer-registry/v1", ingestedAt: layer.updatedAt },
        access: { classification: "internal", allowedRoles: ["viewer", "analyst", "admin", "super_admin"] }
      }))
    };
  });

  app.post<{ Body: QueryBody }>("/v1/query", { preHandler: policy }, async (request, reply) => {
    const body = request.body;
    if (!body || !Array.isArray(body.layerIds) || body.layerIds.length === 0) {
      return reply.code(400).send({ error: "layerIds must contain at least one layer" });
    }
    const limit = Math.max(1, Math.min(Number(body.limit ?? 1000), 5000));
    const registry = await new LayerRegistryService().listLayers();
    const allowed = new Map(
      registry
        .filter((layer) => (request.viewer?.licenses ?? []).includes(layer.licensedFeature))
        .map((layer) => [layer.id, layer])
    );
    const forbiddenLayer = body.layerIds.find((layerId) => !allowed.has(layerId));
    if (forbiddenLayer) {
      return reply.code(403).send({ error: "Layer license required", layerId: forbiddenLayer });
    }
    const items: unknown[] = [];
    for (const layerId of body.layerIds) {
      if (layerId === "maritime.fusion.cable-risk") {
        const events = await upstream<unknown[]>(request, `/v1/fusion/events?limit=${Math.min(limit, 1000)}`);
        items.push(...events);
        continue;
      }
      const params = new URLSearchParams({ layerId, limit: String(Math.min(limit, 2000)) });
      if (body.timeRange?.start) params.set("start_time", body.timeRange.start);
      if (body.timeRange?.end) params.set("end_time", body.timeRange.end);
      if (body.bbox?.length === 4) {
        const [minLon, minLat, maxLon, maxLat] = body.bbox;
        params.set("minLon", String(minLon));
        params.set("minLat", String(minLat));
        params.set("maxLon", String(maxLon));
        params.set("maxLat", String(maxLat));
      }
      const observations = await upstream<unknown[]>(request, `/v1/observations?${params.toString()}`);
      items.push(...observations);
    }
    return { items: items.slice(0, limit) };
  });

  app.get<{ Querystring: { eventType?: string; limit?: string } }>(
    "/v1/events",
    { preHandler: [...policy, requireLicense("subsea:read")] },
    async (request) => {
      const params = new URLSearchParams({ limit: request.query.limit ?? "100" });
      if (request.query.eventType) params.set("eventType", request.query.eventType);
      const events = await upstream<unknown[]>(request, `/v1/fusion/events?${params.toString()}`);
      return { events };
    }
  );
}
