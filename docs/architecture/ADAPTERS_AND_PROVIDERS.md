# Adapters and Providers

This document defines the adapter/provider architecture for external data feeds and the licensing gates required before production use.

## Architecture Plan

- **Provider adapters**: each source is wrapped in an adapter module that returns canonical entities, never raw provider-specific records as public API contracts.
- **Canonical mapping**: adapters map source payloads into stable internal shapes (`CanonicalTrackPoint` for track-like feeds; `PortReference`/`UnlocodeReference` for reference data).
- **Quota + caching**: adapters enforce in-process quota checks and short TTL cache to reduce provider load and absorb transient outages.
- **No secrets exposure**: credentials remain in env/config only; status endpoints should expose booleans and mode flags, never tokens/passwords.
- **Licensing gate**: each dataset gets an explicit `license_tag`; ingest paths must reject writes to unrestricted tables when the feed is marked restricted/non-commercial.

## Implemented Adapters

## OpenSky Adapter

Code: `apps/api/app/modules/integrations/adapters_opensky.py`

- Pulls from OpenSky states endpoint.
- Includes `OpenSkyQuotaManager` (`OPENSKY_RATE_LIMIT_PER_MINUTE`, `OPENSKY_RATE_LIMIT_PER_DAY`).
- Includes TTL cache (`OPENSKY_CACHE_TTL_SEC`).
- Maps state vectors to canonical track points (`CanonicalTrackPoint`).
- Handles outages and quota breaches by returning empty list and logging warnings (no credential leakage).

### Licensing Gate

- OpenSky data usage must follow OpenSky terms; treat as **restricted until legal confirms downstream use case**.
- Tag for internal ingestion policy: `restricted_non_commercial` unless legal overrides.

## World Port Index + UN/LOCODE Importer

Code: `apps/api/app/modules/integrations/importers_ports.py`, `apps/api/app/modules/integrations/models.py`

- Parses CSV extracts for World Port Index and UN/LOCODE.
- Writes to PostGIS-friendly reference tables:
  - `port_references`
  - `unlocode_references`
- Stores:
  - `latitude`, `longitude`
  - `geom_wkt` as `POINT(lon lat)` for later cast to PostGIS geometry/geography
  - `license_tag` for compliance enforcement

### Licensing Gate

- World Port Index and UN/LOCODE should be treated as **restricted/non-commercial by default** until legal confirms redistribution/commercial rights.
- Default tag in importer: `restricted_non_commercial`.

## Restricted Dataset Registry (Current)

- `world_port_index`: **restricted_non_commercial**
- `unlocode`: **restricted_non_commercial**
- `opensky`: **restricted_non_commercial** (pending legal confirmation)

## Planned Adapter Stubs (Not Yet Implemented)

### GFW (Global Fishing Watch)

- Status: planned stub
- Constraint: potential non-commercial and attribution constraints depending on product tier.
- Gate: block production exports until legal review complete.

### TeleGeography

- Status: planned stub
- Constraint: commercial license required; often strict redistribution limits.
- Gate: restricted by default; explicit contract reference required.

### FAA SWIM

- Status: planned stub
- Constraint: regulated access and usage terms by feed/service class.
- Gate: restricted by default; integration only in approved environments.

### EUROCONTROL

- Status: planned stub
- Constraint: controlled aviation data policies and service-specific licenses.
- Gate: restricted by default; legal approval required before customer-facing use.

### Digital NOTAM

- Status: planned stub
- Constraint: aviation safety data with jurisdiction/provider-specific terms.
- Gate: restricted by default; require legal + operational sign-off.

## Enforcement Notes

- Keep ingestion write paths provider-scoped and tag all persisted rows with `license_tag`.
- Build downstream query filters to exclude restricted feeds from commercial/customer exports unless a policy override is explicitly configured.
- Add CI checks to ensure new providers define:
  - canonical mapper tests
  - licensing tag
  - credential redaction checks

