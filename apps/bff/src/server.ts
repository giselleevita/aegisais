import Fastify from "fastify";
import websocket from "@fastify/websocket";
import { config } from "./config.js";
import { authMiddleware } from "./middleware/auth.js";
import { requireLicense } from "./middleware/licensing.js";
import { requireClassification, requireReleasability } from "./middleware/policy.js";
import { registerAuthRoutes } from "./routes/auth.js";
import { registerLayerRoutes } from "./routes/layers.js";
import { registerStreamRoutes } from "./routes/stream.js";
import { ProviderObjectStorage } from "./services/objectStorage.js";

const app = Fastify({ logger: true });

await app.register(websocket);

app.get("/health", async () => ({ status: "ok", env: config.appEnv }));

const objectStorage = new ProviderObjectStorage();
app.get(
  "/v1/storage/status",
  {
    preHandler: [
      authMiddleware,
      requireLicense("admin:org"),
      requireClassification("SECRET"),
      requireReleasability(config.policy.defaultReleasabilityTag),
    ],
  },
  async () => ({
    configured: objectStorage.hasProviderCredentials()
  })
);

await registerAuthRoutes(app);
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
