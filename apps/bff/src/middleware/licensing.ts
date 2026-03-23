import type { FastifyReply, FastifyRequest } from "fastify";

export function requireLicense(feature: string) {
  return async (request: FastifyRequest, reply: FastifyReply): Promise<void> => {
    const licenses = request.viewer?.licenses ?? [];
    if (!licenses.includes(feature)) {
      reply.code(403).send({ error: "License required", feature });
    }
  };
}
