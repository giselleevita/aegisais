import type { LayerManifestItem } from "../types.js";

export class PortsService {
  async getLayers(): Promise<LayerManifestItem[]> {
    return [
      {
        id: "ports-major",
        name: "Major Ports",
        domain: "ports",
        licensedFeature: "ports:read",
        updatedAt: new Date().toISOString(),
        source: "telegeography",
        objectKeyPrefix: "telegeography/ports/major"
      }
    ];
  }
}
