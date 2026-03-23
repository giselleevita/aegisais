import type { FastifyInstance } from "fastify";
import type { RawData, WebSocket } from "ws";
import { config } from "../config.js";
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
