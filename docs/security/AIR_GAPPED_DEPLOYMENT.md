# AegisAIS Air-Gapped Deployment Guide

**Classification:** NATO RESTRICTED | TLP:AMBER  
**Version:** 1.0

## Overview

This guide covers deploying AegisAIS in classified / air-gapped environments
where no external network connectivity is available. Required for environments
operating at NATO RESTRICTED and above.

## Prerequisites

- Container registry mirror (Harbor or similar) within classified network
- PostgreSQL instance within classified perimeter
- Redis instance within classified perimeter
- All dependencies pre-packaged (no pip/npm install from internet)

## Architecture (Air-Gapped)

```
┌──────────────────────────────────────────────────┐
│                NATO RESTRICTED Network             │
│                                                    │
│  ┌─────────┐   ┌──────────┐   ┌──────────────┐   │
│  │ AegisAIS│   │ AegisAIS │   │  AegisAIS    │   │
│  │   Web   │──▶│   BFF    │──▶│    API       │   │
│  └─────────┘   └──────────┘   └──────┬───────┘   │
│                                       │           │
│                    ┌──────────────────┤           │
│                    ▼                  ▼           │
│              ┌──────────┐      ┌──────────┐      │
│              │ PostgreSQL│      │  Redis   │      │
│              └──────────┘      └──────────┘      │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │  Data Diode (one-way AIS feed import)        │ │
│  └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

## Step 1: Build Offline Container Images

On a connected build machine:

```bash
# Build all images
docker build -t aegisais/api:latest apps/api/
docker build -t aegisais/bff:latest apps/bff/
docker build -t aegisais/web:latest apps/web/

# Save to tar archives for transfer
docker save aegisais/api:latest | gzip > aegisais-api.tar.gz
docker save aegisais/bff:latest | gzip > aegisais-bff.tar.gz
docker save aegisais/web:latest | gzip > aegisais-web.tar.gz
```

## Step 2: Transfer via Approved Media

Transfer tar archives to classified environment via approved cross-domain
solution (CDS) or physical media following local security procedures.

```bash
# On classified network — load images
docker load < aegisais-api.tar.gz
docker load < aegisais-bff.tar.gz
docker load < aegisais-web.tar.gz

# Tag for local registry
docker tag aegisais/api:latest registry.local/aegisais/api:latest
docker push registry.local/aegisais/api:latest
```

## Step 3: Configure for Classified Operation

Set the following environment variables:

```env
APP_ENV=production
SECRET_KEY=<generated-on-classified-network>
DATABASE_URL=postgresql://aegisais:<password>@postgres.local:5432/aegisais
REDIS_URL=redis://:<password>@redis.local:6379/0

# Classification defaults (GAP-07)
DEFAULT_CLASSIFICATION=NATO RESTRICTED
DEFAULT_TLP=TLP:AMBER

# Disable external connectivity
SAIS_PROVIDER=none
AISSTREAM_API_KEY=
SANCTIONS_WATCHLIST_PATH=/data/sanctions/watchlist.json

# Security hardening
WEBSOCKET_REQUIRE_AUTH=true
MFA_ENABLED=true
CORS_ALLOWED_ORIGINS=https://aegisais.classified.local
```

## Step 4: Data Import via Data Diode

AIS data enters via one-way data diode:

1. **External collector** receives live AIS feed from aisstream.io / Spire
2. **Data diode** permits one-way transfer of AIS JSON into classified network
3. **AegisAIS import worker** reads from diode landing zone and feeds pipeline

```bash
# Import batch AIS data from diode landing zone
python -m app.scripts.import_ais_batch --input /diode/landing/ais_*.json
```

## Step 5: Sanctions Watchlist Import

```bash
# Transfer sanctions watchlist via CDS
cp /approved-media/sanctions_watchlist.json /data/sanctions/watchlist.json

# Reload in running system
curl -X POST \
	-H "Authorization: Bearer <ADMIN_JWT>" \
	https://aegisais.classified.local/v1/sanctions/watchlist/reload
```

## Step 6: Classification Marking Verification

All data objects include STANAG 4774 classification markings.
Verify with:

```bash
# Check that all API responses include _classification block
curl -s https://aegisais.classified.local/v1/intel/intsum | jq ._classification
# Expected: {"classification": "NATO RESTRICTED", "tlp": "TLP:AMBER", ...}
```

## Step 7: Rehearsal Evidence Capture

Generate the repo-backed rehearsal package before customer-side execution:

```bash
./scripts/finalize_airgap_evidence.sh
```

This writes `docs/evidence/AIR_GAPPED_REHEARSAL_EVIDENCE_FINAL.md` with:

- validation of the compose baseline
- verification that the air-gapped guide and evidence pack are present
- SHA-256 hashes for the core deployment artefacts
- the remaining manual steps required in a real classified environment

## Security Controls

| Control                | Implementation                          |
| ---------------------- | --------------------------------------- |
| Network isolation      | No egress to internet                   |
| Data classification    | STANAG 4774 markings on all objects     |
| Access control         | RBAC + MFA (TOTP)                       |
| Audit logging          | All API calls logged, 90-day retention  |
| Encryption at rest     | PostgreSQL TDE, Redis AUTH              |
| Encryption in transit  | TLS 1.3 only within perimeter           |
| Container hardening    | Non-root, read-only FS, no capabilities |
| Vulnerability scanning | Trivy scan before image transfer        |
