# Layer Catalog

All layers expose source, version, cadence, latency, confidence, access, and provenance.

| id | domain | kind | defaultOn | provider dataset/version | cadence + latency class | licence class | confidence policy | UI rendering + legend | failure mode |
|---|---|---|---|---|---|---|---|---|---|
| `flights.live.opensky` | aviation | dynamic points/tracks | false | OpenSky `states/all` v1 mapped to canonical `Track` | 15-60s poll, near-real-time | `restricted_partner` | observed (0.7-0.95 from completeness/age) | aircraft points + heading vectors, blue/orange by confidence | layer marked degraded; stale timestamp shown |
| `ports.reference.wpi` | maritime | static points | true | NGA World Port Index import snapshot | on-demand import, batch latency | `public_domain` | observed (1.0 snapshot) | cyan points with port code labels | keep last successful snapshot; show import age |
| `ports.reference.unlocode` | logistics | static reference | false | UNECE UN/LOCODE release | biannual import, batch latency | `open` | observed (1.0 snapshot) | metadata enrichment badges on ports/entities | fallback to prior release snapshot |
| `subsea.cables.telegeo` | infrastructure | static polylines | false | TeleGeography drop (geojson/json), versioned import | manual import, batch latency | `commercial` | observed when licensed import exists; else simulated placeholder | magenta cable lines; legend includes licence badge | if missing license/data, show placeholder + restricted banner |
| `subsurface.inferred_interest` | maritime-security | inferred polygons | false | derived from fused rules + context model version | event-driven recompute, analytical latency | `tenant` | inferred (0.3-0.8, explainable factors required) | semi-transparent red/orange heat zones | disabled when model/context unavailable; show reason |
| `fishing.events.gfw` | maritime | events | false | Global Fishing Watch events/port visits/gaps | provider cadence, deferred ingest | `noncommercial_only` | observed where feed exists; otherwise unavailable | event glyphs with non-commercial badge | hidden unless entitlement flag enabled |
| `notam.digital.stub` | aviation | event overlays | false | FAA SWIM/EUROCONTROL/Digital NOTAM connector stubs | none (stub) | `restricted_partner` | simulation (0.0) until credentials | grey dashed overlay placeholders | show “partner integration required” |

## Metadata Contract Requirements

Every layer object in API/UI includes:

- `source.provider`, `source.dataset`, `source.version`
- `refresh.cadence`, `refresh.latencyClass`
- `confidence.class`, `confidence.score`
- `access.level` (`public`, `tenant`, `partner`, `admin`)
- `provenance.text`

## Compliance Controls

- Restricted and non-commercial layers are default-off and visibly badged.
- BFF enforces licensing gates before returning layer manifest entries.
- Browser never receives provider tokens.
