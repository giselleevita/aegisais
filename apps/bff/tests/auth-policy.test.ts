import assert from "node:assert/strict";
import { afterEach, beforeEach, test } from "node:test";
import Fastify, { type FastifyInstance } from "fastify";
import { config } from "../src/config.js";
import { registerAuthRoutes } from "../src/routes/auth.js";
import { registerLayerRoutes } from "../src/routes/layers.js";

function makeJwt(claims: Record<string, unknown>): string {
  const header = Buffer.from(JSON.stringify({ alg: "none", typ: "JWT" })).toString("base64url");
  const payload = Buffer.from(JSON.stringify(claims)).toString("base64url");
  return `${header}.${payload}.sig`;
}

function authHeader(token: string): { authorization: string } {
  return { authorization: `Bearer ${token}` };
}

let app: FastifyInstance;

beforeEach(async () => {
  config.appEnv = "development";
  config.auth.enforceInDevelopment = false;
  config.auth.issuer = "";
  config.auth.audience = "";
  config.auth.jwksUrl = "";
  config.policy.defaultReleasabilityTag = "NATO";

  app = Fastify();
  await registerAuthRoutes(app);
  await registerLayerRoutes(app);
});

afterEach(async () => {
  await app.close();
});

test("returns 401 when bearer token is missing", async () => {
  const res = await app.inject({ method: "GET", url: "/v1/auth/context" });

  assert.equal(res.statusCode, 401);
  assert.deepEqual(res.json(), { error: "Missing bearer token" });
});

test("returns 401 when token format is invalid", async () => {
  const res = await app.inject({
    method: "GET",
    url: "/v1/auth/context",
    headers: authHeader("not-a-jwt"),
  });

  assert.equal(res.statusCode, 401);
  assert.deepEqual(res.json(), { error: "Invalid bearer token" });
});

test("rejects layers manifest when classification is below required level", async () => {
  const token = makeJwt({
    sub: "analyst-1",
    org_id: "org-1",
    role: "analyst",
    licenses: ["ports:read"],
    clearances: ["RESTRICTED"],
    releasability: ["NATO"],
  });

  const res = await app.inject({
    method: "GET",
    url: "/v1/layers/manifest",
    headers: authHeader(token),
  });

  assert.equal(res.statusCode, 403);
  assert.deepEqual(res.json(), {
    error: "Insufficient classification clearance",
    required: "CONFIDENTIAL",
    effective: "RESTRICTED",
  });
});

test("rejects layers manifest when releasability tag is missing", async () => {
  const token = makeJwt({
    sub: "analyst-2",
    org_id: "org-1",
    role: "analyst",
    licenses: ["ports:read"],
    clearances: ["SECRET"],
    releasability: ["USA"],
  });

  const res = await app.inject({
    method: "GET",
    url: "/v1/layers/manifest",
    headers: authHeader(token),
  });

  assert.equal(res.statusCode, 403);
  assert.deepEqual(res.json(), {
    error: "Insufficient releasability",
    required: "NATO",
  });
});

test("allows layers manifest with valid claims and returns licensed layers", async () => {
  const token = makeJwt({
    sub: "analyst-3",
    org_id: "org-1",
    role: "analyst",
    licenses: ["ports:read"],
    clearances: ["SECRET"],
    releasability: ["NATO", "USA"],
  });

  const res = await app.inject({
    method: "GET",
    url: "/v1/layers/manifest",
    headers: authHeader(token),
  });

  assert.equal(res.statusCode, 200);
  const body = res.json() as { layers: Array<{ id: string; licensedFeature: string }>; generatedAt: string };
  assert.ok(Array.isArray(body.layers));
  assert.equal(body.layers.length, 1);
  assert.equal(body.layers[0].id, "ports-major");
  assert.equal(body.layers[0].licensedFeature, "ports:read");
  assert.match(body.generatedAt, /^\d{4}-\d{2}-\d{2}T/);
});

test("returns normalized claims in auth context", async () => {
  const token = makeJwt({
    sub: "supervisor-1",
    org_id: "org-77",
    role: "supervisor",
    licenses: ["ports:read", "incidents:read"],
    clearances: ["secret", "confidential"],
    releasability: ["nato", "usa"],
  });

  const res = await app.inject({
    method: "GET",
    url: "/v1/auth/context",
    headers: authHeader(token),
  });

  assert.equal(res.statusCode, 200);
  const body = res.json() as {
    viewer: {
      userId: string;
      organizationId: string;
      role: string;
      clearances: string[];
      releasability: string[];
      licenses: string[];
    };
    claims: {
      role: string;
      clearances: string[];
      releasability: string[];
      licenses: string[];
    };
    timestamp: string;
  };

  assert.equal(body.viewer.userId, "supervisor-1");
  assert.equal(body.viewer.organizationId, "org-77");
  assert.equal(body.viewer.role, "supervisor");
  assert.deepEqual(body.claims.clearances, ["SECRET", "CONFIDENTIAL"]);
  assert.deepEqual(body.claims.releasability, ["NATO", "USA"]);
  assert.deepEqual(body.claims.licenses, ["ports:read", "incidents:read"]);
  assert.match(body.timestamp, /^\d{4}-\d{2}-\d{2}T/);
});
