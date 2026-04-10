import type { FastifyInstance } from "fastify";
import { authMiddleware } from "../middleware/auth.js";

export async function registerAuthRoutes(app: FastifyInstance): Promise<void> {
  app.get("/v1/auth/context", { preHandler: authMiddleware }, async (request) => {
    const viewer = request.viewer;
    return {
      viewer,
      claims: {
        role: viewer?.role ?? "guest",
        clearances: viewer?.clearances ?? [],
        releasability: viewer?.releasability ?? [],
        licenses: viewer?.licenses ?? [],
      },
      timestamp: new Date().toISOString(),
    };
  });
}
