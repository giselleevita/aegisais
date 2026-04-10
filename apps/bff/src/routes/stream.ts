import type { FastifyInstance, RouteHandlerMethod } from "fastify";
import type { RawData, WebSocket } from "ws";
import { config } from "../config.js";

// @fastify/websocket augments RouteShorthandOptions but its package has no
// "exports" field, so the module augmentation is not picked up automatically
// under "moduleResolution": "NodeNext". Mirror the declaration locally.
declare module "fastify" {
  interface RouteShorthandOptions {
    websocket?: boolean;
  }
}
import { authMiddleware } from "../middleware/auth.js";
import { requireLicense } from "../middleware/licensing.js";

type ClientMessage = { type?: string };

export async function registerStreamRoutes(app: FastifyInstance): Promise<void> {
  app.register(async (wsApp) => {
    // Route overloads for websocket handlers are not consistently resolved in this workspace setup.
    const wsHeartbeatHandler = ((socket: WebSocket) => {
      const timer = setInterval(() => {
        socket.send(
          JSON.stringify({
            type: "heartbeat",
            ts: new Date().toISOString()
          })
        );
      }, config.wsHeartbeatMs);

      socket.on("message", (raw: RawData) => {
        let parsed: ClientMessage | null = null;
        try {
          parsed = JSON.parse(raw.toString()) as ClientMessage;
        } catch {
          socket.send(JSON.stringify({ type: "error", error: "Invalid JSON payload" }));
          return;
        }
        if (parsed.type === "ping") {
          socket.send(JSON.stringify({ type: "pong", ts: new Date().toISOString() }));
        }
      });

      socket.on("close", () => {
        clearInterval(timer);
      });
    }) as unknown as RouteHandlerMethod;

    wsApp.get(
      "/v1/stream",
      {
        websocket: true,
        preHandler: [authMiddleware, requireLicense("ports:read")]
      },
      wsHeartbeatHandler
    );
  });
}
