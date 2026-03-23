import type { FastifyReply, FastifyRequest } from "fastify";
import type { ViewerContext } from "../types.js";

declare module "fastify" {
  interface FastifyRequest {
    viewer?: ViewerContext;
  }
}

const DEFAULT_LICENSES = ["aviation:read", "ports:read"];

export async function authMiddleware(request: FastifyRequest, reply: FastifyReply): Promise<void> {
  const authorization = request.headers.authorization;
  if (!authorization || !authorization.startsWith("Bearer ")) {
    reply.code(401).send({ error: "Missing bearer token" });
    return;
  }

  request.viewer = {
    userId: "stub-user",
    organizationId: "stub-org",
    licenses: DEFAULT_LICENSES
  };
}
