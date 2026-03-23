import Fastify from "fastify";
import websocket from "@fastify/websocket";
import { config } from "./config.js";
import { registerLayerRoutes } from "./routes/layers.js";
import { registerStreamRoutes } from "./routes/stream.js";
import { ProviderObjectStorage } from "./services/objectStorage.js";

const app = Fastify({ logger: true });

await app.register(websocket);

app.get("/health", async () => ({ status: "ok", env: config.appEnv }));

const objectStorage = new ProviderObjectStorage();
app.get("/v1/storage/status", async () => ({
  configured: objectStorage.hasProviderCredentials()
}));

await registerLayerRoutes(app);
await registerStreamRoutes(app);

const start = async () => {
  try {
    await app.listen({ host: config.host, port: config.port });
  } catch (error) {
    app.log.error(error);
    process.exit(1);
  }
};

void start();
