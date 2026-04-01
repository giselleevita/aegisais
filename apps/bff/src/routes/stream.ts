import type { FastifyInstance } from "fastify";
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
    wsApp.get(
      "/v1/stream",
      {
        websocket: true,
        preHandler: [authMiddleware, requireLicense("ports:read")]
      },
      // @ts-expect-error: @fastify/websocket adds a RouteShorthandMethod overload
      // where the handler receives (socket: WebSocket) when websocket:true, but its
      // module augmentation is not loaded under "moduleResolution":"NodeNext" (no
      // exports field). Runtime behaviour is correct — ws.WebSocket is passed here.
      (socket: WebSocket) => {
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
      }
    );
  });
}
