# Three-Minute Festival Demo — Is the Vessel Still There?

## Before the audience arrives

- Run `scripts/festival_preflight.sh` and keep its report.
- Sign in as an administrator, open **Admin**, select **Reset**, then open **Map**.
- Keep cable zones, AIS tracks, SAR detections, fused risk, and alerts enabled.
- The primary flow is local replay. A live AIS feed is background context only.

## 0:00–0:30 — The operational question

> “A vessel’s AIS says it left—or simply goes silent—near critical infrastructure. Is the vessel actually gone?”

Show the Baltic common operating picture and cable corridor. Start the **Berlin festival scenario** from Admin, then return to the map.

State explicitly: the scenario is a deterministic simulation using the same contracts as the live adapters.

## 0:30–1:10 — Normal transit versus suspicious behavior

- Point to the blue AIS tracks.
- The normal cargo vessel crosses at transit speed without a cable-risk alert.
- The research vessel slows below three knots and changes course inside the 1,500 m protection threshold.
- A medium-confidence `VESSEL_ACTIVITY_NEAR_CABLE` event appears.

> “AegisAIS separates proximity from intent. Crossing a cable is ordinary; sustained low-speed activity is not.”

## 1:10–2:00 — AIS silence and independent sensing

- The suspicious vessel’s AIS track stops.
- An orange diamond appears: an unmatched SAR vessel detection after 35 logical minutes of AIS silence.
- Open the `UNMATCHED_SAR_NEAR_CABLE` alert.

> “The independent observation does not inherit the AIS identity. It remains an unresolved sensor target, and the system preserves that uncertainty.”

## 2:00–2:40 — Explainability and evidence

Show:

- Cable distance and configured threshold.
- AIS silence duration.
- Contributing observation IDs and sensor layers.
- Confidence method and provenance lineage.
- Model/rule version and deterministic reason.

> “This confidence is evidence quality and corroboration—not a claim that the system knows hostile intent.”

Mention that the anomaly model reports an empirical percentile, not a probability, and rules remain active if the model is unavailable.

## 2:40–3:00 — Deployment path

> “Today this is a multi-sensor decision-support prototype with validated replay performance. The next step is a sustained operator pilot using licensed satellite AIS, SAR/RF feeds, and external CoT/NFFI receivers.”

Ask for:

- A Baltic or North Sea pilot area.
- Operator feedback on escalation thresholds.
- A sensor or procurement partner for independent validation.

## Fallback

If venue connectivity fails, continue normally: replay, infrastructure geometry, observations, model artifact, and evidence are local. If the browser or stack fails, use the pre-recorded walkthrough and the one-page evidence sheet. Never relabel replay or historical GFW data as live.
