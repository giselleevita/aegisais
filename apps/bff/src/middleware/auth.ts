import type { FastifyReply, FastifyRequest } from "fastify";
import { createRemoteJWKSet, decodeJwt, jwtVerify, type JWTPayload } from "jose";
import { config } from "../config.js";
import type { ClassificationLevel, ViewerContext } from "../types.js";

declare module "fastify" {
  interface FastifyRequest {
    viewer?: ViewerContext;
  }
}

const DEFAULT_LICENSES = ["aviation:read", "ports:read"];
const CLASSIFICATION_ORDER: Record<ClassificationLevel, number> = {
  UNCLASSIFIED: 0,
  RESTRICTED: 1,
  CONFIDENTIAL: 2,
  SECRET: 3,
  TOP_SECRET: 4,
};
const CLASSIFICATION_ALIASES: Record<string, ClassificationLevel> = {
  UNCLASSIFIED: "UNCLASSIFIED",
  U: "UNCLASSIFIED",
  RESTRICTED: "RESTRICTED",
  CONFIDENTIAL: "CONFIDENTIAL",
  C: "CONFIDENTIAL",
  SECRET: "SECRET",
  S: "SECRET",
  TOP_SECRET: "TOP_SECRET",
  TS: "TOP_SECRET",
};

let remoteJwks: ReturnType<typeof createRemoteJWKSet> | null = null;

function shouldEnforceVerification(): boolean {
  return config.appEnv === "production" || config.auth.enforceInDevelopment;
}

function getRemoteJwks(): ReturnType<typeof createRemoteJWKSet> | null {
  if (!config.auth.jwksUrl) return null;
  if (!remoteJwks) {
    remoteJwks = createRemoteJWKSet(new URL(config.auth.jwksUrl));
  }
  return remoteJwks;
}

function firstString(v: unknown): string | null {
  return typeof v === "string" && v.trim().length > 0 ? v.trim() : null;
}

function asStringArray(v: unknown): string[] {
  if (!Array.isArray(v)) return [];
  return v
    .map((x) => (typeof x === "string" ? x.trim() : ""))
    .filter((x) => x.length > 0);
}

function extractClaim(payload: Record<string, unknown> | null, keys: string[]): unknown {
  if (!payload) return undefined;
  for (const key of keys) {
    const value = payload[key];
    if (value !== undefined && value !== null) return value;
  }
  return undefined;
}

function resolveRole(payload: Record<string, unknown> | null): ViewerContext["role"] {
  if (!payload) return "analyst";
  const candidates = [
    firstString(payload.role),
    ...asStringArray(payload.roles),
    ...asStringArray(payload.groups),
  ]
    .filter((x): x is string => !!x)
    .map((x) => x.toLowerCase());

  if (candidates.some((x) => x.includes("admin") || x.includes("owner"))) return "admin";
  if (candidates.some((x) => x.includes("supervisor") || x.includes("lead") || x.includes("manager"))) {
    return "supervisor";
  }
  return "analyst";
}

function resolveLicenses(payload: Record<string, unknown> | null): string[] {
  if (!payload) return [];
  const licenses = new Set<string>();
  asStringArray(payload.licenses).forEach((v) => licenses.add(v));
  asStringArray(payload.permissions).forEach((v) => licenses.add(v));

  const scope = firstString(payload.scope);
  if (scope) {
    scope
      .split(/\s+/)
      .filter((x) => x.includes(":"))
      .forEach((x) => licenses.add(x));
  }

  const realmAccess = payload.realm_access;
  if (realmAccess && typeof realmAccess === "object") {
    asStringArray((realmAccess as { roles?: unknown }).roles).forEach((v) => licenses.add(v));
  }

  return Array.from(licenses);
}

function normalizeClassification(value: unknown): ClassificationLevel | null {
  if (typeof value !== "string") return null;
  const normalized = value.trim().toUpperCase().replace(/\s+/g, "_");
  return CLASSIFICATION_ALIASES[normalized] ?? null;
}

function resolveClearances(payload: Record<string, unknown> | null): ClassificationLevel[] {
  if (!payload) return [];
  const values = [
    ...asStringArray(extractClaim(payload, ["clearances", "clearance_levels"])),
    firstString(extractClaim(payload, ["clearance", "classification"])),
  ].filter((v): v is string => !!v);

  const clearances = Array.from(new Set(values.map((v) => normalizeClassification(v)).filter((v): v is ClassificationLevel => !!v)));
  return clearances.sort((a, b) => CLASSIFICATION_ORDER[b] - CLASSIFICATION_ORDER[a]);
}

function resolveReleasability(payload: Record<string, unknown> | null): string[] {
  if (!payload) return [];
  const values = [
    ...asStringArray(extractClaim(payload, ["releasability", "release_to", "caveats"])),
    firstString(extractClaim(payload, ["releasability_tag"])),
  ].filter((v): v is string => !!v);

  return Array.from(new Set(values.map((v) => v.toUpperCase().trim())));
}

async function parseAndVerifyToken(token: string): Promise<Record<string, unknown> | null> {
  const jwks = getRemoteJwks();
  if (!jwks || !config.auth.issuer || !config.auth.audience) {
    if (shouldEnforceVerification()) {
      throw new Error("JWT verification config is incomplete");
    }
    try {
      return decodeJwt(token) as Record<string, unknown>;
    } catch {
      return null;
    }
  }

  const { payload } = await jwtVerify(token, jwks, {
    issuer: config.auth.issuer,
    audience: config.auth.audience,
    clockTolerance: "30s",
  });
  return payload as JWTPayload as Record<string, unknown>;
}

export async function authMiddleware(request: FastifyRequest, reply: FastifyReply): Promise<void> {
  const authorization = request.headers.authorization;
  if (!authorization || !authorization.startsWith("Bearer ")) {
    reply.code(401).send({ error: "Missing bearer token" });
    return;
  }

  const token = authorization.slice("Bearer ".length).trim();
  let payload: Record<string, unknown> | null = null;
  try {
    payload = await parseAndVerifyToken(token);
  } catch {
    reply.code(401).send({ error: "Invalid bearer token" });
    return;
  }

  if (!payload) {
    reply.code(401).send({ error: "Invalid bearer token" });
    return;
  }

  const role = resolveRole(payload);
  const claimedLicenses = resolveLicenses(payload);
  const clearances = resolveClearances(payload);
  const releasability = resolveReleasability(payload);
  const isProduction = config.appEnv === "production";
  const licenses = claimedLicenses.length > 0 ? claimedLicenses : (isProduction ? [] : DEFAULT_LICENSES);
  const userId = firstString(payload?.sub) ?? firstString(payload?.user_id) ?? "jwt-user";
  const organizationId = firstString(payload?.org_id) ?? firstString(payload?.tenant) ?? "jwt-org";

  request.viewer = {
    userId,
    organizationId,
    role,
    clearances,
    releasability,
    licenses,
  };
}
