# External Integrations Setup Guide

This guide documents how to configure and enable each external data source and service integration for AegisAIS.

## Overview

AegisAIS integrates with multiple external providers for AIS data, vessel context, and threat intelligence. Each integration requires:

- API credentials (keys, tokens, authentication)
- Configuration files or environment variables
- Connection verification and health checks
- Optional: production deployment considerations

---

## 1. AIStream.io (Primary AIS Feed)

### Purpose

Real-time AIS terrestrial coverage. Primary data source for live vessel tracking.

### Setup Steps

1. **Obtain API Key**
   - Visit https://www.aisstream.io
   - Create account or use existing credentials
   - Generate API key from account dashboard
   - Note: Rate limits vary by subscription tier (demo: 50 msgs/sec, paid: 5000+ msgs/sec)

2. **Configure Credentials**

   ```bash
   # In apps/api/.env
   AISSTREAM_API_KEY=your_actual_api_key_here
   AISSTREAM_SUBSCRIPTION_KEY=your_subscription_key
   ```

3. **Enable in Pipeline**

   Currently, the AIStream adapter is **scaffolding only** and not wired to the processing pipeline. To enable:
   - File: `apps/api/app/modules/integrations/adapters_aisstream.py`
   - Status: WebSocket client implemented, message parsing ready
   - TODO: Wire to `ingestion/stream.py` in the ITDAE pipeline
   - Action: See [BFF Stream Integration](#bff-stream-integration) below

4. **Verify Connection**
   ```bash
   cd apps/api
   python -c "
   from app.modules.integrations.adapters_aisstream import AIStreamWebSocketClient
   client = AIStreamWebSocketClient(api_key='YOUR_KEY')
   # Test connection
   "
   ```

### Production Considerations

- AIStream limits are per subscription tier; monitor `messages_received` metrics
- WebSocket reconnection logic: automatic with exponential backoff (1s → 60s)
- Data freshness: typical 5–30 second latency depending on region

---

## 2. OpenSky Network (Vessel Context and Airborne Tracking)

### Purpose

Aircraft/helicopter interception data and vessel transponder locations.

### Setup Steps

1. **Obtain Credentials**
   - Free tier: https://opensky-network.org/myaccount/profile
   - Paid tier (recommended for production): contact sales@opensky-network.org
   - Free tier rate limit: 4 requests/10 seconds, limited historical data access
   - Paid tier: custom rate limits, full historical archive

2. **Configure Credentials**

   ```bash
   # In apps/api/.env
   OPENSKY_USERNAME=your_username
   OPENSKY_PASSWORD=your_password
   OPENSKY_RATE_LIMIT_CALLS=4       # Free tier
   OPENSKY_RATE_LIMIT_PERIOD=10     # seconds
   ```

3. **License Restrictions**
   - ⚠️ **CRITICAL**: Free tier is "restricted for non-commercial use"
   - Production/commercial deployment requires paid subscription
   - Academic/research: contact OpenSky for special licensing
   - File: `apps/api/app/modules/integrations/adapters_opensky.py` contains license check

4. **Integration Point**
   - Used by: `apps/api/app/modules/analyst/router.py` → `enrich_vessel_context()`
   - Called on-demand when analyst views vessel details
   - Fallback: if OpenSky unavailable, system shows AIS data only

### Production Considerations

- Implement circuit breaker (fail open to AIS-only mode)
- Cache results: 15–60 minutes per vessel MMSI
- Monitor quota usage; alert if approaching limits
- Rate limiter: `app/services/opensky_rate_limiter.py` enforces call throttling

---

## 3. SAIS (STANAG Exchange Format Receiver)

### Purpose

NATO-formatted message receiver. Consumes STANAG-formatted XML/JSON from coalition systems.

### Setup Steps

1. **Deployment Context**
   - Typically deployed in sovereign or air-gapped environments
   - Requires NATO coalition network access (SIPNET, DISN, or equivalent)
   - See: [docs/security/AIR_GAPPED_DEPLOYMENT.md](AIR_GAPPED_DEPLOYMENT.md)

2. **Configuration**

   ```bash
   # In apps/api/.env
   SAIS_RECEIVER_PORT=9001                    # Listening port
   SAIS_VALIDATOR_STRICT=true                 # Enforce full STANAG compliance
   SAIS_TELEMETRY_RETENTION_DAYS=90           # How long to store telemetry
   ```

3. **Message Format Support**
   - COT (Cursor-on-Target) XML format
   - NFFI (NATO Friendly Force Information) XML format
   - Custom JSON schema (contract-based)
   - See: `packages/contracts/schemas/` for schema definitions

4. **Test Data**
   - Sample messages: `apps/api/docs/evidence/d04_sample_*.xml`
   - Receiver rehearsal: `apps/api/docs/evidence/d04_receiver_rehearsal_*.xml`
   - Test scripts: `apps/api/scripts/generate_d04_interop_samples.py`

5. **Verify Receiver**
   ```bash
   cd apps/api
   python scripts/test_sais_receiver.py  # If available, or manually test with nc/curl
   ```

---

## 4. Sanctions Data (External Screening Lists)

### Purpose

Cross-reference vessel/owner against international sanctions and screening databases.

### Data Sources

1. **OFAC SDN List** (US Treasury)
   - URL: https://home.treasury.gov/policy-issues/office-of-foreign-assets-control-sanctions-list-data
   - Format: CSV/XML
   - Update frequency: Daily
   - Integration: `apps/api/app/modules/sanctions/official_lists.py`

2. **EU Consolidated Sanctions List**
   - URL: https://data.europa.eu/api/hub/store/search?query=sanctions
   - Format: XML/JSON
   - Update frequency: Weekly
   - Coverage: EU and international persons/entities

3. **UN Security Council Consolidated List**
   - URL: https://www.un.org/securitycouncil/sanctions/information
   - Format: PDF/XML
   - Update frequency: As updated

### Setup Steps

1. **Configure Data Source Refresh**

   ```bash
   # In apps/api/.env
   SANCTIONS_REFRESH_INTERVAL_HOURS=24     # How often to pull latest lists
   SANCTIONS_OFAC_ENABLED=true
   SANCTIONS_EU_ENABLED=true
   SANCTIONS_UN_ENABLED=true
   ```

2. **Initialize Sanctions Database**

   ```bash
   cd apps/api
   python -c "
   from app.modules.sanctions.service import SanctionsService
   service = SanctionsService()
   service.refresh_all_lists()  # Fetch latest data
   "
   ```

3. **Verify Coverage**
   - Test vessel: Run `apps/api/tests/test_sanctions_api.py`
   - Expected: System finds matches for known sanctioned entities

### Production Considerations

- Initial load may take 5–10 minutes
- Subsequent refreshes are incremental
- Alert if refresh fails; fall back to cached data
- OFAC list includes ~1000+ individuals/entities; EU list ~500+

---

## 5. IoT/Telemetry Ingest (Subsea Sensors and Edge Devices)

### Purpose

Collect environmental telemetry, ASW (anti-submarine warfare) sensor data, and maritime surveillance from edge infrastructure.

### Setup Steps

1. **MQTT Broker Configuration**

   ```bash
   # In apps/api/.env
   MQTT_BROKER_HOST=mqtt.internal.example.com
   MQTT_BROKER_PORT=8883                      # TLS port
   MQTT_USERNAME=aegisais-ingest
   MQTT_PASSWORD=<strongly-random>
   MQTT_TOPIC_SENSORS=sensors/+/telemetry
   MQTT_TOPIC_ASW=operations/asw/readings
   ```

2. **Device Registration**
   - Endpoint: `POST /api/iot/devices`
   - Schema: `packages/contracts/schemas/Device.schema.json`
   - Required: device_id, device_type, location, org_id
   - See: `apps/api/app/modules/iot/models.py` for full schema

3. **Sensor Heartbeat Configuration**

   ```json
   {
     "device_id": "SENSOR-NOR-001",
     "device_type": "subsea_sensor",
     "location": { "lat": 60.5, "lon": 5.0 },
     "heartbeat_interval_seconds": 300,
     "telemetry_schema_version": "1.0"
   }
   ```

4. **Start IoT Ingest Service**
   ```bash
   cd apps/api
   python -m app.infrastructure.iot.mqtt_consumer  # Start MQTT listener
   ```

---

## 6. BFF Stream Integration (Gateway Configuration)

### Purpose

The Backend-for-Frontend (BFF) Fastify gateway aggregates and streams real-time data to the web UI.

### Current Status

- ✅ WebSocket endpoint implemented: `GET /stream`
- ✅ Message routing and serialization ready
- ❌ Not yet connected to AIStream or SAIS receivers

### To Enable Live Streaming

1. **Wire AIStream to Pipeline** (TODO)
   - File: `apps/api/app/modules/itdae/ingestion/stream.py`
   - Change: `if AISSTREAM_ENABLED:` block (currently commented)
   - Action: Uncomment and test

2. **Configure BFF to Forward Events**

   ```typescript
   // apps/bff/src/routes/stream.ts
   import { streamAisUpdates } from "../integrations/ais-pipeline";

   router.get("/stream", (req, res) => {
     // Currently returns static demo data
     // TODO: Call streamAisUpdates() to get live feed
   });
   ```

3. **Health Check**
   ```bash
   curl http://localhost:3001/health  # Should return { status: "healthy" }
   ```

---

## 7. Verification and Monitoring

### Post-Configuration Checklist

- [ ] API credentials securely stored (use .env, not hardcoded)
- [ ] Each integration tested with sample data
- [ ] Health check endpoints monitored in production
- [ ] Rate limits and quotas tracked
- [ ] Error logs reviewed for integration failures
- [ ] Data freshness SLAs defined (e.g., "AIS data ≤ 30 seconds old")

### Monitoring Dashboard

Check integration health at:

- API: `GET /api/health/integrations` (lists status of all providers)
- BFF: `GET /health` (basic gateway status)
- Logs: `docker logs aegisais-api` for integration errors

### Common Issues

| Issue                   | Solution                                                  |
| ----------------------- | --------------------------------------------------------- |
| "API key invalid"       | Verify key format; check expiration; regenerate if needed |
| "Rate limit exceeded"   | Implement backoff; upgrade subscription tier              |
| "Connection timeout"    | Check network routing; verify firewall rules              |
| "SSL certificate error" | Update CA bundles; check certificate expiration           |
| "No data received"      | Verify subscription is active; check topic names for IoT  |

---

## Next Steps

1. **For Development**: Use demo credentials from `infra/docker/.env`; run `docker-compose up` to start all services including MQTT broker
2. **For Staging**: Contact platform admins for integration credentials
3. **For Production**: Follow [Production Secrets Management](PRODUCTION_SECRETS_MANAGEMENT.md) runbook
4. **For NATO Deployment**: See [Classified Environment Setup](AIR_GAPPED_DEPLOYMENT.md)
