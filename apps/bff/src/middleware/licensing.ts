/**
 * BL-008: Authoritative license gate middleware.
 *
 * Keeps a registry of ALL valid licensed features. Any request presenting an
 * unknown feature string is rejected even before the viewer's license list is
 * checked — this prevents privilege escalation by forging license strings.
 *
 * Viewer licenses are populated by the auth middleware from a backend-validated
 * JWT/session. The gate here enforces them at the route level.
 */
import type { FastifyReply, FastifyRequest } from "fastify";

/**
 * Canonical set of valid licensed features.
 * Every feature string that can be claimed in a bearer token must appear here.
 * Unknown strings are rejected as invalid regardless of what the viewer claims.
 */
const KNOWN_FEATURES = new Set<string>([
  "aviation:read",
  "ports:read",
  "subsea:read",
  "alerts:read",
  "incidents:read",
  "incidents:write",
  "analytics:read",
  "export:csv",
  "export:pdf",
  "admin:org",
]);

export function requireLicense(feature: string) {
  // Fail fast at startup if a route references an unknown feature string
  if (!KNOWN_FEATURES.has(feature)) {
    throw new Error(
      `requireLicense: unknown feature "${feature}". Add it to KNOWN_FEATURES in licensing.ts.`
    );
  }

  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    const licenses = request.viewer?.licenses ?? [];

    // Reject any license claim that is not in the authoritative set (defence-in-depth)
    const validClaims = licenses.filter((l) => KNOWN_FEATURES.has(l));

    if (!validClaims.includes(feature)) {
      reply.code(403).send({ error: "License required", feature });
    }
  };
}

