import type { LayerManifestItem } from "../types.js";

/** Canonical maritime layers used by the festival replay and live adapters. */
export class MaritimeService {
  async getLayers(): Promise<LayerManifestItem[]> {
    const updatedAt = new Date().toISOString();
    return [
      {
        id: "maritime.ais.terrestrial",
        name: "Terrestrial AIS",
        domain: "maritime",
        licensedFeature: "subsea:read",
        updatedAt,
        source: "AISStream or attributed replay",
        objectKeyPrefix: "maritime/ais/terrestrial/",
        mode: "live",
        licenceClass: "provider_terms",
        confidenceMethod: "provider_and_completeness"
      },
      {
        id: "maritime.ais.satellite",
        name: "Satellite AIS",
        domain: "maritime",
        licensedFeature: "subsea:read",
        updatedAt,
        source: "Configured S-AIS provider",
        objectKeyPrefix: "maritime/ais/satellite/",
        mode: "live",
        licenceClass: "commercial",
        confidenceMethod: "provider_and_completeness"
      },
      {
        id: "maritime.sar.gfw",
        name: "Sentinel-1 SAR vessel detections",
        domain: "maritime",
        licensedFeature: "subsea:read",
        updatedAt,
        source: "Global Fishing Watch / Copernicus Sentinel-1",
        objectKeyPrefix: "maritime/sar/gfw/",
        mode: "historical_replay",
        licenceClass: "noncommercial_only",
        confidenceMethod: "provider_detection_score"
      },
      {
        id: "maritime.fusion.cable-risk",
        name: "Fused cable-risk events",
        domain: "maritime",
        licensedFeature: "subsea:read",
        updatedAt,
        source: "AegisAIS fusion engine",
        objectKeyPrefix: "maritime/fusion/cable-risk/",
        mode: "derived",
        licenceClass: "tenant",
        confidenceMethod: "independent_sensor_corroboration"
      }
    ];
  }
}
