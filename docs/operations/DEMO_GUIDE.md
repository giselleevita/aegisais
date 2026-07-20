# Festival Demo Operations Guide

## Start

```bash
scripts/start_festival_demo.sh
```

This validates the fixture and model artifact, builds the local Docker stack, applies migrations, and starts the API, processing, persistence, observation, alert, BFF, web, database, and Redis services.

Open the web console at `http://localhost:5174`. The local API is available at `http://localhost:8000`; the canonical BFF is available at `http://localhost:8081`.

## Run the scenario

1. Sign in with an administrator account.
2. Open **Admin & control plane**.
3. Select **Reset**.
4. Select **Start 3-minute demo**.
5. Open **Map** and enable AIS, SAR, fused cable risk, alerts, and cable zones.
6. Open the final dark-vessel alert to show confidence and provenance.

At 20× playback the five observations emit in approximately three seconds of wall time, while retaining a 45-minute logical sensor timeline. Increase or decrease `speed` through the API if a slower presentation is preferred.

## Preflight

```bash
scripts/festival_preflight.sh
```

The command checks:

- Compose syntax and required services.
- Canonical contract and scenario JSON validity.
- Isolation Forest artifact/manifest hash and feature schema.
- Backend imports and frontend typecheck/build prerequisites.
- API, database, Redis, and model health when the stack is already running.

Do not demonstrate if the preflight reports a fixture, migration, contract, or artifact-hash failure.

## Offline behavior

- Scenario data, cable geometry, SAR detections, and model artifacts are local.
- Live AIS, satellite AIS, GFW, and RF providers may be disconnected without blocking replay.
- The analyst console marks unavailable or stale feeds instead of showing an empty feed as healthy.
- Docker defaults to `VITE_OFFLINE_DEMO=true`, which disables remote tiles and renders a bundled Natural Earth Baltic land/coastline vector beneath cable, track, sensor, and alert overlays. Set it to `false` only when an approved connected basemap is available.
- The clipped 1:50m vector is public-domain Natural Earth data; attribution and source details ship in `apps/web/public/maps/ATTRIBUTION.md`.

## Reset behavior

Reset removes only festival fusion alerts, their incidents, festival observations, and festival fusion events for the signed-in organisation. It does not erase unrelated tenant data.

## Claims discipline

- Say “synthetic replay” for the packaged scenario.
- Say “historical SAR detections” for GFW data.
- Say “empirical anomaly percentile,” never “probability of hostile activity.”
- Say “multi-sensor decision-support prototype,” not “field-proven autonomous surveillance.”
