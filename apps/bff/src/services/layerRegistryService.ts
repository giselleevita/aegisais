import type { LayerManifestItem } from "../types.js";
import { AviationService } from "./aviationService.js";
import { PortsService } from "./portsService.js";
import { SubseaService } from "./subseaService.js";

export class LayerRegistryService {
  constructor(
    private readonly aviation = new AviationService(),
    private readonly ports = new PortsService(),
    private readonly subsea = new SubseaService()
  ) {}

  async listLayers(): Promise<LayerManifestItem[]> {
    const [aviationLayers, portsLayers, subseaLayers] = await Promise.all([
      this.aviation.getLayers(),
      this.ports.getLayers(),
      this.subsea.getLayers()
    ]);
    return [...aviationLayers, ...portsLayers, ...subseaLayers];
  }
}
