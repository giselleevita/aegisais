import { config } from "../config.js";

export interface ObjectStorage {
  list(prefix: string): Promise<string[]>;
  put(key: string, payload: Buffer): Promise<void>;
}

export class ProviderObjectStorage implements ObjectStorage {
  async list(prefix: string): Promise<string[]> {
    return [`${prefix}/latest.json`];
  }

  async put(_key: string, _payload: Buffer): Promise<void> {
    return;
  }

  // Keep provider tokens server-side only.
  hasProviderCredentials(): boolean {
    return Boolean(config.provider.teleGeographyToken || config.provider.eoProviderToken);
  }
}
