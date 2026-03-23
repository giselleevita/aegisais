import type { LayerManifestItem } from "../types.js";

export class SubseaService {
  async getLayers(): Promise<LayerManifestItem[]> {
    return [
      {
        id: "subsea-cables",
        name: "Subsea Cables",
        domain: "subsea",
        licensedFeature: "subsea:read",
        updatedAt: new Date().toISOString(),
        source: "telegeography",
        objectKeyPrefix: "telegeography/subsea/cables"
      }
    ];
  }
}
