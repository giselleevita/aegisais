export type LayerDomain = "aviation" | "ports" | "subsea" | "maritime";

export type ClassificationLevel =
  | "UNCLASSIFIED"
  | "RESTRICTED"
  | "CONFIDENTIAL"
  | "SECRET"
  | "TOP_SECRET";

export interface LayerManifestItem {
  id: string;
  name: string;
  domain: LayerDomain;
  licensedFeature: string;
  updatedAt: string;
  source: string;
  objectKeyPrefix: string;
  mode?: "live" | "historical_replay" | "derived";
  licenceClass?: string;
  confidenceMethod?: string;
}

export interface ViewerContext {
  userId: string;
  organizationId: string;
  role: "guest" | "analyst" | "supervisor" | "admin";
  clearances: ClassificationLevel[];
  releasability: string[];
  licenses: string[];
}
