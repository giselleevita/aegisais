CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS data_sources (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,
  dataset_key TEXT NOT NULL,
  object_prefix TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (provider, dataset_key)
);

CREATE TABLE IF NOT EXISTS layer_registry (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  layer_id TEXT NOT NULL UNIQUE,
  display_name TEXT NOT NULL,
  domain TEXT NOT NULL CHECK (domain IN ('aviation', 'ports', 'subsea')),
  licensed_feature TEXT NOT NULL,
  source_id UUID REFERENCES data_sources (id) ON DELETE SET NULL,
  bbox GEOMETRY(POLYGON, 4326),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_layer_registry_domain ON layer_registry (domain);
CREATE INDEX IF NOT EXISTS idx_layer_registry_bbox ON layer_registry USING GIST (bbox);

CREATE TABLE IF NOT EXISTS layer_assets (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  layer_id UUID NOT NULL REFERENCES layer_registry (id) ON DELETE CASCADE,
  object_key TEXT NOT NULL,
  format TEXT NOT NULL,
  checksum_sha256 TEXT,
  version_tag TEXT,
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (layer_id, object_key)
);

CREATE TABLE IF NOT EXISTS ingest_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  provider TEXT NOT NULL,
  dataset_key TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('started', 'succeeded', 'failed')),
  started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  finished_at TIMESTAMPTZ,
  details JSONB NOT NULL DEFAULT '{}'::jsonb
);
