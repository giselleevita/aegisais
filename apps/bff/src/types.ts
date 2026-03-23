export type LayerDomain = "aviation" | "ports" | "subsea";

export interface LayerManifestItem {
  id: string;
  name: string;
  domain: LayerDomain;
  licensedFeature: string;
  updatedAt: string;
  source: string;
  objectKeyPrefix: string;
}

export interface ViewerContext {
  userId: string;
  organizationId: string;
  licenses: string[];
}
