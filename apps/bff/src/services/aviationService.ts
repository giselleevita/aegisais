import type { LayerManifestItem } from "../types.js";

export class AviationService {
  async getLayers(): Promise<LayerManifestItem[]> {
    return [
      {
        id: "aviation-airspaces",
        name: "Aviation Airspaces",
        domain: "aviation",
        licensedFeature: "aviation:read",
        updatedAt: new Date().toISOString(),
        source: "telegeography",
        objectKeyPrefix: "telegeography/aviation/airspaces"
      }
    ];
  }
}
