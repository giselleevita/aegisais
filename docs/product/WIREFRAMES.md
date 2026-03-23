# Wireframes

## 3D Globe Analyst Workbench (`/globe`)

```text
+--------------------------------------------------------------------------------------+
| HEADER: AEGISAIS Analyst | Auth | Stream status                                      |
+--------------------------------------------------------------------------------------+
| NAV: Operations | Map | Lab | ITDAE | Globe | Watchlist | Admin | About            |
+--------------------------------------------------------------------------------------+
| Layer Catalogue                |                    3D Globe                    |    |
|-------------------------------|--------------------------------------------------|Ins |
| [x] Flights Live              |                                                  |pec |
|     BFF-backed tracks         |              Cesium world canvas                |tor |
| [x] Ports                     |      - flights markers (live/replay)            |----|
|     Major reference points    |      - ports points + labels                    |Lay |
| [ ] Subsea Cables [Restricted]|      - subsea cable polylines (or placeholder)  |er  |
|     [Non-commercial]          |                                                  |Prov|
|                               |                                                  |Conf|
|                               |                                                  |Src |
|                               |                                                  |Acc |
|                               |                                                  |Lic |
+--------------------------------------------------------------------------------------+
| Timeline: [Live] [Replay]  | status text                                         |
+--------------------------------------------------------------------------------------+
```

## Interaction notes

- Layer row click opens inspector for that layer.
- Layer checkbox toggles visibility on globe.
- `Restricted` and `Non-commercial` badges are always visible for gated entries.
- Timeline toggle updates flight rendering mode and viewer clock behavior.

## Mobile degradation (future)

For narrow widths, collapse into stacked panels:

1. Globe
2. Timeline
3. Layer catalogue
4. Inspector drawer (slide-over)

This is out of scope for the current desktop-first increment.
