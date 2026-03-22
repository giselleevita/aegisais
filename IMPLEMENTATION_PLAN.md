# AegisAIS — Implementation Plan
### Investor-Readiness & Enterprise Deployment Hardening

> **Purpose:** This plan takes AegisAIS from a working research-grade MVP to an enterprise-deployable
> maritime security platform suitable for pilot customer engagement and Seed-stage investor due diligence.
>
> **Derived from:** Seed fundraising package analysis of `/Users/yusaf/aegisais/` and Confluence docs.
>
> **Working directory for all tasks:** `/Users/yusaf/aegisais/`

---

## How to Use This Plan in Cursor

Paste each task block into **Cursor Composer (Agent mode)** one sprint at a time.
Each task references exact file paths and describes the precise change required.
Do not skip Sprint 1 — it blocks every other sprint.

---

## Sprint 1 — Security Hardening
**Timeline:** 2–3 weeks | **Priority:** CRITICAL — blocks enterprise deployment

All items in this sprint are known security gaps documented in the Confluence Risk Register.
None of these are optional before showing the product to a paying customer or an investor doing
technical due diligence.

---

### Task 1.1 — Enforce SECRET_KEY validation at startup
**File:** `apps/api/app/core/config.py`
**Problem:** `secret_key: str = "supersecretkey"` — a default insecure key will be used if
the environment variable is not set. An investor doing any technical DD will find this
immediately and it signals that the product is not production-ready.

**What to build:**
- Add a Pydantic `@field_validator` on `secret_key` that raises `ValueError` if the value is
  `"supersecretkey"` or shorter than 32 characters when `APP_ENV` is not `"development"` or `"test"`.
- Add a new `app_env: str = "development"` field to `Settings` sourced from `APP_ENV` env var.
- Add a module-level startup check after `settings = Settings()` that calls a `validate_production_config()`
  function — it should log a CRITICAL warning and raise `RuntimeError` if `secret_key` is the default
  value and `app_env == "production"`.
- Update `.env.example` (create it if it does not exist at `apps/api/.env.example`) with all required
  env vars, each with a comment. Include: `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`,
  `APP_ENV`, `WEBSOCKET_REQUIRE_AUTH`, `CORS_ALLOWED_ORIGINS`.

---

### Task 1.2 — Reduce JWT access token lifetime and add refresh token flow
**Files:**
- `apps/api/app/core/config.py`
- `apps/api/app/modules/auth/service.py`
- `apps/api/app/modules/auth/api/routes_auth.py`
- `apps/api/app/modules/auth/models.py` (new `RefreshToken` model)

**Problem:** `access_token_expire_minutes: int = 43200` — this is 30 days.
A 30-day JWT cannot be revoked without a token blacklist. If a token is stolen, the attacker
has 30 days of access. This is a HIGH security risk documented in the Confluence Risk Register.

**What to build:**

1. In `config.py`:
   - Change `access_token_expire_minutes` default to `60` (1 hour).
   - Add `refresh_token_expire_days: int = 7`.

2. In `models.py`, add a `RefreshToken` SQLAlchemy model to the `users` table schema:
   ```
   id, token_hash (SHA-256 of the raw token, String, unique, indexed),
   user_id (FK → users.id), expires_at (DateTime), revoked (Boolean default False),
   created_at (DateTime default now)
   ```

3. In `service.py`:
   - Add `create_refresh_token(user_id: int, db: Session) -> str` — generates a
     `secrets.token_urlsafe(64)` raw token, stores its SHA-256 hash in `RefreshToken`,
     returns the raw token.
   - Add `verify_refresh_token(raw_token: str, db: Session) -> Optional[User]` — looks up
     the hash, checks `revoked=False` and `expires_at > now()`, returns the User or None.
   - Add `revoke_refresh_token(raw_token: str, db: Session) -> bool`.

4. In `routes_auth.py`:
   - Update `POST /login` response to return both `access_token` and `refresh_token`.
     The refresh token must be set as an `HttpOnly`, `Secure`, `SameSite=Strict` cookie
     AND returned in the response body (operators may need both patterns).
   - Add `POST /refresh` endpoint: reads refresh token from cookie or request body,
     calls `verify_refresh_token`, issues a new access token.
   - Add `POST /logout` endpoint: calls `revoke_refresh_token` for the current session,
     clears the cookie.

5. Create an Alembic migration for the `refresh_tokens` table:
   ```bash
   cd apps/api && alembic revision --autogenerate -m "add_refresh_tokens"
   ```

---

### Task 1.3 — Add token revocation / blacklist for access tokens
**Files:**
- `apps/api/app/modules/auth/service.py`
- `apps/api/app/modules/auth/dependencies.py`
- `apps/api/app/infrastructure/cache/redis_client.py` (add helper if not present)

**Problem:** Even with a 60-minute access token, there is no way to immediately revoke a
compromised token without a blacklist. For government buyers this is a hard requirement.

**What to build:**
- Add `revoke_access_token(token: str) -> None` in `service.py` — stores the token's
  `jti` (JWT ID) claim in Redis with a TTL equal to the token's remaining lifetime.
  Use key pattern `aegisais:revoked_jti:{jti}`.
- Update `create_access_token` to inject a `jti` claim (`secrets.token_urlsafe(16)`).
- Update `decode_access_token` to check if the `jti` is in the Redis revoked set.
  If Redis is unavailable, log a WARNING and allow the token (fail-open during Redis outage,
  log for audit — document this trade-off with a comment).
- Update `POST /logout` in `routes_auth.py` to also call `revoke_access_token` for the
  current access token.

---

### Task 1.4 — Add TLS termination and reverse proxy via nginx
**Files:**
- `infra/docker/docker-compose.yml`
- `infra/docker/nginx/nginx.conf` (create)
- `infra/docker/nginx/Dockerfile` (create, or use official nginx image)

**Problem:** No TLS at the application layer. This is a HIGH risk documented in Confluence.
No government or enterprise buyer will send credentials or operational data over unencrypted HTTP.

**What to build:**

1. Add an `nginx` service to `docker-compose.yml`:
   ```yaml
   nginx:
     image: nginx:1.27-alpine
     ports:
       - "80:80"
       - "443:443"
     volumes:
       - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
       - ./nginx/certs:/etc/nginx/certs:ro   # mount TLS certs
     depends_on:
       - api
   ```
   Remove the direct `ports: "8000:8000"` mapping from the `api` service so the API
   is only reachable through nginx.

2. Create `infra/docker/nginx/nginx.conf` with:
   - HTTP → HTTPS redirect on port 80.
   - HTTPS termination on port 443 with `ssl_certificate` and `ssl_certificate_key`
     paths pointing to the mounted cert volume.
   - `proxy_pass http://api:8000` for all HTTPS traffic.
   - Security headers: `Strict-Transport-Security`, `X-Content-Type-Options`,
     `X-Frame-Options`, `X-XSS-Protection`, `Referrer-Policy`, `Content-Security-Policy`.
   - WebSocket proxy support: `proxy_http_version 1.1`, `Upgrade`, `Connection` headers
     for the `/v1/stream` path.

3. Create `infra/docker/nginx/README.md` with instructions for:
   - Generating a self-signed cert for development: `openssl req -x509 ...`
   - Mounting a Let's Encrypt cert for staging/production.
   - Using Certbot with the nginx container.

---

### Task 1.5 — Add Redis authentication to docker-compose
**Files:**
- `infra/docker/docker-compose.yml`
- `apps/api/app/core/config.py`

**Problem:** Redis is unauthenticated by default. Any process that can reach the Redis port
can read/write AIS stream data and rate limit state. MEDIUM risk in Confluence.

**What to build:**
1. Add a `requirepass` command to the Redis service in `docker-compose.yml`:
   ```yaml
   redis:
     image: redis:7-alpine
     command: redis-server --requirepass ${REDIS_PASSWORD}
     ...
   ```
2. Update all services that use `REDIS_URL` to use the authenticated URL format:
   `redis://:${REDIS_PASSWORD}@redis:6379/0`
3. Add `REDIS_PASSWORD` to the `Settings` class in `config.py` with an empty string default
   and the same production validator pattern used for `secret_key` (fail if empty in production).
4. Add `REDIS_PASSWORD` to `.env.example`.

---

### Task 1.6 — Enforce WebSocket authentication in production
**Files:**
- `apps/api/app/core/config.py`
- `apps/api/app/infrastructure/ws/manager.py`

**Problem:** `websocket_require_auth: bool = False` — WebSocket is unauthenticated by default.
Any client can connect to `/v1/stream` and receive real-time vessel positions and alerts
without any credentials. This is unacceptable for an operational deployment.

**What to build:**
1. Change the default to `websocket_require_auth: bool = True`.
2. Update the `APP_ENV`-aware startup validator (Task 1.1) to also assert that
   `websocket_require_auth` is `True` in production and raise a `RuntimeError` if not.
3. In `manager.py`, add a clear log message when WebSocket auth is disabled explaining
   this is development mode only.
4. Update the frontend WebSocket client in `apps/web/src/core/ws-url.ts` to read the
   JWT access token from local storage / auth context and append it as `?token=<JWT>`
   to the WebSocket URL when connecting.

---

### Task 1.7 — Lock down CORS to configurable allowed origins
**Files:**
- `apps/api/app/main.py`
- `apps/api/app/core/config.py`

**Problem:** `allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"]`
— CORS is hardcoded to localhost origins. In production this should only allow the actual
frontend domain.

**What to build:**
1. Add `cors_allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]`
   to `Settings`, sourced from a `CORS_ALLOWED_ORIGINS` env var (comma-separated string,
   parsed with a `@field_validator`).
2. In `main.py`, replace the hardcoded list with `settings.cors_allowed_origins`.
3. Add `CORS_ALLOWED_ORIGINS=https://your-frontend-domain.com` to `.env.example`
   with a comment explaining the production value.

---

### Task 1.8 — Add security headers middleware
**Files:**
- `apps/api/app/middleware/security_headers.py` (create)
- `apps/api/app/main.py`

**Problem:** No security headers are set on API responses (no HSTS, no X-Frame-Options,
no Content-Security-Policy for the `/docs` Swagger UI). MEDIUM risk in Confluence.

**What to build:**
1. Create `apps/api/app/middleware/security_headers.py` with a Starlette `BaseHTTPMiddleware`
   that adds to every response:
   - `X-Content-Type-Options: nosniff`
   - `X-Frame-Options: DENY`
   - `X-XSS-Protection: 1; mode=block`
   - `Referrer-Policy: strict-origin-when-cross-origin`
   - Do NOT add `Strict-Transport-Security` here — that is handled by nginx (Task 1.4).
2. Register the middleware in `main.py` with `app.add_middleware(SecurityHeadersMiddleware)`.

---

### Task 1.9 — Add rate limiting to all sensitive API routes
**Files:**
- `apps/api/app/middleware/rate_limit.py`
- `apps/api/app/api/v1/vessels.py`
- `apps/api/app/api/v1/alerts.py`
- `apps/api/app/modules/itdae/api/routes_itdae.py`
- `apps/api/app/api/v1/audit.py`

**Problem:** Rate limiting currently only covers auth login, register, and upload routes.
All other endpoints (vessel queries, alert queries, ITDAE, audit) are unprotected.

**What to build:**
1. Create three new shared rate limit instances in `rate_limit.py`:
   ```python
   api_read_rate_limit = rate_limit_dependency(100, 60, name="api_read")
   api_write_rate_limit = rate_limit_dependency(30, 60, name="api_write")
   ws_connect_rate_limit = rate_limit_dependency(5, 60, name="ws_connect")
   ```
2. Apply `api_read_rate_limit` as a `Depends()` to all `GET` route handlers in
   `vessels.py`, `alerts.py`, `routes_itdae.py`, and `audit.py`.
3. Apply `api_write_rate_limit` to all `POST`, `PATCH`, `PUT`, `DELETE` handlers
   that are not already rate limited.
4. Apply `ws_connect_rate_limit` at the start of the `stream` WebSocket handler
   in `manager.py` before `ws.accept()`.

---

### Task 1.10 — Add User model `created_at` and `last_login` fields
**Files:**
- `apps/api/app/modules/auth/models.py`
- `apps/api/app/modules/auth/api/routes_auth.py`

**Problem:** The `User` model has no timestamp fields. Enterprise buyers require audit
trails that include when accounts were created and when they last authenticated.

**What to build:**
1. Add to the `User` model:
   - `created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)`
   - `updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)`
   - `last_login = Column(DateTime(timezone=True), nullable=True)`
2. Update `POST /login` in `routes_auth.py` to set `user.last_login = datetime.now(timezone.utc)`
   and commit after successful login.
3. Create an Alembic migration: `alembic revision --autogenerate -m "add_user_timestamps"`.

---

### Sprint 1 Verification Checklist
After completing all Sprint 1 tasks, verify:
- [ ] `SECRET_KEY=supersecretkey` with `APP_ENV=production` raises `RuntimeError` on startup
- [ ] `POST /v1/auth/login` returns both `access_token` (1-hour TTL) and `refresh_token`
- [ ] `POST /v1/auth/refresh` issues a new access token from a valid refresh token
- [ ] `POST /v1/auth/logout` revokes both tokens; subsequent requests with old token return 401
- [ ] `GET /v1/stream` (WebSocket) returns `1008` without a valid `?token=` in production mode
- [ ] All API routes return `X-Content-Type-Options: nosniff` header
- [ ] `GET /v1/vessels` returns `429` after 101 requests within 60 seconds
- [ ] Redis requires password; connection without password returns `NOAUTH` error
- [ ] `docker-compose up` with nginx serving HTTPS on port 443
- [ ] `pytest` passes with no regressions

---

## Sprint 2 — Operational Reliability
**Timeline:** 1–2 weeks after Sprint 1 | **Priority:** HIGH — required for first pilot deployment

---

### Task 2.1 — Block SQLite in non-development environments
**Files:**
- `apps/api/app/core/config.py`
- `apps/api/app/core/database.py`

**Problem:** `database_url: str = "sqlite:///./aegisais.db"` — SQLite will be silently
used if `DATABASE_URL` is not set. An operator who forgets to set this env var will run
a production system on SQLite. SQLite does not support concurrent async writes from
multiple workers. This is a data-loss risk.

**What to build:**
1. Add `@field_validator("database_url")` in `Settings` that:
   - Raises `ValueError` if the URL starts with `sqlite` and `app_env` is `"production"`.
   - Logs a `WARNING` if the URL starts with `sqlite` and `app_env` is not `"development"`.
2. In `database.py`, add an engine creation check: if `database_url` contains `sqlite`,
   set `connect_args={"check_same_thread": False}` (already standard). If not SQLite,
   configure connection pool settings from config: `pool_size`, `max_overflow`, `pool_timeout`.
3. Add pool config fields to `Settings`:
   - `db_pool_size: int = 10`
   - `db_max_overflow: int = 20`
   - `db_pool_timeout: int = 30`
   - `db_pool_recycle: int = 1800`

---

### Task 2.2 — Add health checks and restart policies to all Docker services
**File:** `infra/docker/docker-compose.yml`

**Problem:** No `healthcheck` or `restart` policies on any services. If the API or a worker
crashes, Docker does not restart it. This means a pilot customer could experience silent
failures with no recovery.

**What to build:**
Update `docker-compose.yml` to add to every service:

1. **`db` (PostgreSQL):**
   ```yaml
   healthcheck:
     test: ["CMD-SHELL", "pg_isready -U aegisais -d aegisais"]
     interval: 10s
     timeout: 5s
     retries: 5
   restart: unless-stopped
   ```

2. **`redis`:**
   ```yaml
   healthcheck:
     test: ["CMD", "redis-cli", "--no-auth-warning", "-a", "${REDIS_PASSWORD}", "ping"]
     interval: 10s
     timeout: 5s
     retries: 5
   restart: unless-stopped
   ```

3. **`api`:**
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:8000/v1/health"]
     interval: 15s
     timeout: 10s
     retries: 3
     start_period: 20s
   restart: unless-stopped
   depends_on:
     db:
       condition: service_healthy
     redis:
       condition: service_healthy
   ```

4. **All workers** (`processing-worker`, `persistence-worker`, `alert-worker`,
   `itdae-ingestion`):
   ```yaml
   restart: unless-stopped
   depends_on:
     db:
       condition: service_healthy
     redis:
       condition: service_healthy
   ```

---

### Task 2.3 — Add worker liveness probes
**Files:**
- `apps/api/app/services/workers/processing_worker.py`
- `apps/api/app/services/workers/persistence_worker.py`
- `apps/api/app/services/workers/alert_worker.py`

**Problem:** Workers have no liveness mechanism. Docker `healthcheck` for the API uses
the `/v1/health` endpoint, but the workers have no HTTP server. If a worker hangs silently
(blocked Redis read, unhandled exception in the processing loop), Docker has no signal
to restart it.

**What to build:**
For each worker, add a "heartbeat file" liveness probe pattern:
1. Each worker writes a timestamp to a temp file (`/tmp/worker_{name}_heartbeat`) every
   N seconds of successful loop iterations (every 30s or every 100 messages, whichever
   comes first).
2. Add a `healthcheck` to each worker service in `docker-compose.yml` that checks the
   heartbeat file's modification time:
   ```yaml
   healthcheck:
     test: ["CMD-SHELL", "test $(( $(date +%s) - $(stat -c %Y /tmp/worker_processing_heartbeat) )) -lt 120"]
     interval: 30s
     timeout: 10s
     retries: 3
     start_period: 30s
   ```
3. Add a `restart: unless-stopped` policy to all worker services.

---

### Task 2.4 — Add automated database backup service
**File:** `infra/docker/docker-compose.yml`
**New file:** `infra/docker/backup/backup.sh`

**Problem:** No backup strategy documented or implemented. A pilot customer losing their
alert history due to a disk failure would be a customer-ending event.

**What to build:**
1. Create `infra/docker/backup/backup.sh`:
   - Uses `pg_dump` to dump the `aegisais` database to a compressed file.
   - Filename pattern: `aegisais_backup_$(date +%Y%m%d_%H%M%S).sql.gz`
   - Saves to `/backups/` volume mount.
   - Deletes backups older than `BACKUP_RETENTION_DAYS` (default 7).
   - Exits non-zero on failure (so Docker logs the error).

2. Add a `backup` service to `docker-compose.yml`:
   ```yaml
   backup:
     image: postgres:16
     environment:
       POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-aegisais}
       PGPASSWORD: ${POSTGRES_PASSWORD:-aegisais}
       BACKUP_RETENTION_DAYS: ${BACKUP_RETENTION_DAYS:-7}
     volumes:
       - ./backup/backup.sh:/backup.sh:ro
       - aegisais_backups:/backups
     command: >
       sh -c "while true; do sleep 86400; sh /backup.sh; done"
     depends_on:
       db:
         condition: service_healthy
     restart: unless-stopped
   ```

3. Add `aegisais_backups:` to the `volumes:` section of `docker-compose.yml`.

---

### Task 2.5 — Add Prometheus alert rules for worker failures
**New files:**
- `infra/monitoring/prometheus.yml`
- `infra/monitoring/alert_rules.yml`
- `infra/monitoring/grafana/` (optional dashboard provisioning)

**Problem:** Prometheus metrics are exposed at `/metrics` but there are no alert rules or
Grafana dashboards. Without these, an operator has no visibility into worker lag or failures.

**What to build:**
1. Create `infra/monitoring/prometheus.yml`:
   ```yaml
   global:
     scrape_interval: 15s
   scrape_configs:
     - job_name: 'aegisais'
       static_configs:
         - targets: ['api:8000']
   rule_files:
     - 'alert_rules.yml'
   ```

2. Create `infra/monitoring/alert_rules.yml` with rules for:
   - `AegisAISStreamLagHigh`: fires if `aegisais_stream_lag > 1000` for 5 minutes.
   - `AegisAISWorkerDown`: fires if the `api` target is unreachable for 2 minutes.
   - `AegisAISHighAlertRate`: fires if alert generation rate exceeds 100/min (possible feed issue).
   - `AegisAISNoPositionsProcessed`: fires if `aegisais_positions_processed_total` hasn't
     increased in 10 minutes (suggests ingestion stalled).

3. Add `prometheus` service to `docker-compose.yml`:
   ```yaml
   prometheus:
     image: prom/prometheus:v3.3.1
     volumes:
       - ../monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
       - ../monitoring/alert_rules.yml:/etc/prometheus/alert_rules.yml:ro
       - aegisais_prometheus:/prometheus
     ports:
       - "9090:9090"
     restart: unless-stopped
   ```

---

### Task 2.6 — Create comprehensive `.env.example`
**File:** `apps/api/.env.example` (create if not present)

**Problem:** There is no `.env.example` in the repository. A new operator has no reference
for what environment variables are required. This causes misconfiguration at deployment time.

**What to build:**
Create `apps/api/.env.example` with every env var used in `Settings`, grouped and commented:

```bash
# ============================================================
# AegisAIS — Environment Configuration
# Copy this file to .env and fill in all required values.
# Lines marked [REQUIRED] will cause startup failure if empty in production.
# ============================================================

# --- Application ---
APP_ENV=development         # development | staging | production [REQUIRED in prod]

# --- Security [REQUIRED] ---
SECRET_KEY=                 # openssl rand -hex 32
REDIS_PASSWORD=             # openssl rand -hex 16

# --- Database [REQUIRED] ---
DATABASE_URL=postgresql+psycopg://aegisais:aegisais@localhost:5432/aegisais

# --- Redis [REQUIRED] ---
REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:6379/0

# --- JWT ---
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# --- WebSocket ---
WEBSOCKET_REQUIRE_AUTH=true    # Set false ONLY for local development

# --- CORS ---
# Comma-separated list of allowed frontend origins
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# --- ITDAE ---
ITDAE_AIS_API_KEY=            # API key for live AIS data provider (optional)
ITDAE_BALTIC_BBOX=            # Bounding box for Baltic AIS feed filter

# --- Rate Limiting ---
RATE_LIMIT_USE_REDIS=true     # Use Redis for distributed rate limiting (recommended in prod)

# --- Audit Logging ---
ENABLE_AUDIT_LOGGING=true
AUDIT_LOG_RETENTION_DAYS=90

# --- Database Connection Pool ---
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=1800

# --- Backups ---
BACKUP_RETENTION_DAYS=7
```

---

### Sprint 2 Verification Checklist
- [ ] Starting API with `DATABASE_URL` pointing to SQLite and `APP_ENV=production` raises `RuntimeError`
- [ ] `docker-compose up` — all services healthy after 60s (`docker-compose ps` shows `healthy`)
- [ ] Stopping the processing worker causes Docker to restart it within 30s
- [ ] Backup service creates a `.sql.gz` file in the `aegisais_backups` volume on schedule
- [ ] Prometheus at `http://localhost:9090` shows AegisAIS target as UP
- [ ] `pytest` still passes with no regressions

---

## Sprint 3 — Feature Completeness
**Timeline:** 2–4 weeks after Sprint 2 | **Priority:** HIGH — required for enterprise pilot

---

### Task 3.1 — ITDAE zone management API (replace hardcoded geofences)
**Files:**
- `apps/api/app/modules/itdae/geofences/baltic_cables.py` (existing — becomes seed data)
- `apps/api/app/modules/itdae/models.py` (create or update — add `ITDAEZone` model)
- `apps/api/app/modules/itdae/api/routes_itdae.py` (add CRUD endpoints)
- `apps/api/app/modules/itdae/geofences/checker.py` (update to read from DB)

**Problem:** All geofence zones are hardcoded in `baltic_cables.py`. An enterprise customer
needs to define their own protected zones (their specific cable routes, not the generic Baltic
zones). This is listed as a Sprint 3 item in the Confluence Risk Register.

**What to build:**

1. Create `ITDAEZone` SQLAlchemy model:
   ```python
   id, name (String), description (String), risk_level (Enum: low/medium/high/critical),
   polygon_geojson (JSON — GeoJSON Polygon geometry), is_active (Boolean default True),
   created_by (FK → users.id), created_at, updated_at
   ```

2. Create a database seeder that reads from `BALTIC_CABLE_ZONES` in `baltic_cables.py`
   and inserts them into the `itdae_zones` table on first startup (idempotent — check
   by `name` before inserting).

3. Add CRUD endpoints to `routes_itdae.py`:
   - `GET /api/v1/itdae/zones` — list all active zones (auth required, analyst role)
   - `POST /api/v1/itdae/zones` — create zone (admin only), accepts GeoJSON Polygon
   - `GET /api/v1/itdae/zones/{zone_id}` — get zone detail
   - `PATCH /api/v1/itdae/zones/{zone_id}` — update zone (admin only)
   - `DELETE /api/v1/itdae/zones/{zone_id}` — soft-delete zone / set `is_active=False` (admin only)

4. Update `checker.py` `get_zone_for_position()` and `get_all_zones_for_position()` to
   accept an optional `zones` parameter (list of zone dicts). Update calling code to pass
   zones fetched from the database. Add a Redis cache layer: cache the full zone list with
   a 5-minute TTL (key: `aegisais:itdae_zones`), invalidated on any zone create/update/delete.

5. Create Alembic migration: `alembic revision --autogenerate -m "add_itdae_zones_table"`.

---

### Task 3.2 — ITDAE zone management UI (React)
**Files:**
- `apps/web/src/features/itdae/components/ZoneManager.tsx` (create)
- `apps/web/src/features/itdae/hooks/useZones.ts` (create)
- `apps/web/src/App.tsx` (add Zones tab, admin-only)

**Problem:** Even with the API built (Task 3.1), operators need a UI to manage zones.
Without this, enterprise customers must use the Swagger UI or raw curl to manage geofences —
which is not acceptable for non-technical operators.

**What to build:**
1. Create `useZones.ts` hook using the `fetch` API (or existing api-client pattern):
   - `GET /api/v1/itdae/zones` → returns zone list
   - `POST`, `PATCH`, `DELETE` wrappers with JWT auth headers
   - Loading, error, and success state management

2. Create `ZoneManager.tsx` component (admin role only):
   - Table view of all zones: name, risk_level, is_active, created_at, action buttons
   - "Add Zone" modal with a form: name (text), description (textarea), risk_level (select),
     and a Leaflet map where the admin can draw a polygon (use Leaflet.draw or similar)
   - "Edit Zone" modal (pre-populated)
   - "Deactivate" toggle with confirmation dialog

3. In `App.tsx`, add a "Zones" tab visible only when the current user has `role === "admin"`.

---

### Task 3.3 — Vessel watchlist feature
**Files:**
- `apps/api/app/modules/vessels/models.py` (add `WatchlistEntry` model)
- `apps/api/app/modules/vessels/api/routes_vessels.py` (add watchlist endpoints)
- `apps/web/src/features/vessels/components/WatchlistPanel.tsx` (create)

**Problem:** Analysts need to flag specific MMSIs for priority monitoring (known suspicious
vessels, vessels of interest from intelligence reports). Without a watchlist, every vessel
has equal priority in the alert feed. Watchlist is listed as a Sprint 3 item in Confluence.

**What to build:**

1. Backend model `WatchlistEntry`:
   ```python
   id, mmsi (String, indexed), label (String — analyst's note),
   priority (Enum: low/medium/high), added_by (FK → users.id),
   created_at, is_active (Boolean)
   ```

2. API endpoints:
   - `GET /v1/watchlist` — list active watchlist entries (analyst role)
   - `POST /v1/watchlist` — add MMSI to watchlist (analyst/admin)
   - `DELETE /v1/watchlist/{mmsi}` — remove from watchlist (analyst/admin)

3. Update the alert processing pipeline: when an alert is generated for a vessel that is
   in the watchlist, set a `watchlist_priority` flag in the alert evidence JSON.
   Watchlisted vessel alerts should surface first in the alert panel.

4. In the frontend, create `WatchlistPanel.tsx`:
   - Shows all watched MMSIs with their labels and priority
   - "Add to watchlist" button on the vessel detail view
   - Watchlisted vessels highlighted (different colour) on the Leaflet map

5. Create Alembic migration: `alembic revision --autogenerate -m "add_watchlist"`.

---

### Task 3.4 — Real-time alert status sync via WebSocket
**Files:**
- `apps/api/app/modules/alerts/service.py`
- `apps/api/app/infrastructure/ws/manager.py`
- `apps/web/src/features/alerts/hooks/useAlerts.ts` (or existing hooks)

**Problem:** Alert status changes (acknowledge, resolve, false_positive) are made via
`PATCH /v1/alerts/{id}/status` but are not broadcast over the WebSocket. If two analysts
are working simultaneously, one analyst's status changes are invisible to the other until
they manually refresh. This is listed as a Sprint 3 item in Confluence.

**What to build:**
1. In `alerts/service.py`, after a successful status update, call `broadcast()` from
   `ws/manager.py` with a payload:
   ```json
   {
     "type": "alert_status_updated",
     "alert_id": 123,
     "status": "resolved",
     "updated_by": "analyst_username",
     "timestamp": "2026-03-22T10:00:00Z"
   }
   ```

2. In the frontend alert hooks, add a WebSocket message handler for `alert_status_updated`
   messages that updates the relevant alert in local state without requiring a full refetch.

---

### Task 3.5 — File upload security hardening (content validation)
**Files:**
- `apps/api/app/api/v1/upload.py`

**Problem:** File uploads are validated by extension and path only. An attacker could
upload a malformed CSV with embedded code, extremely large column values, or a decompressed
bomb (zst file that decompresses to terabytes). The Confluence Risk Register lists "malware
scanning on upload" as a Sprint 3 item.

**What to build:**
1. Add decompression bomb protection for `.zst` files: before processing, check the
   decompressed size using `zstandard`'s `ZstdDecompressor` frame parameters.
   Reject if decompressed size > `MAX_DECOMPRESSED_SIZE_GB` (configurable, default 50GB).

2. Add CSV header validation: before accepting a file for processing, read the first 4KB,
   check that the required column names are present (use the existing flexible name matching
   logic). Reject with a clear error if the required columns are missing.

3. Add a `uploaded_files` audit log entry via `AuditService.log_event` on every successful
   upload (file name, size, uploader username, timestamp).

4. Add `scan_uploads_for_malware: bool = False` to `Settings`. When `True`, pipe the file
   through a configurable virus scanner endpoint (leave the actual scanner implementation
   as a stub with a clear `TODO` comment and a feature flag — ClamAV integration is a
   follow-on task).

---

### Sprint 3 Verification Checklist
- [ ] Admin can create a custom geofence zone via the UI; it appears on the map
- [ ] Detection engine uses DB zones, not hardcoded `BALTIC_CABLE_ZONES`
- [ ] Analyst can add a vessel to the watchlist; alerts for that vessel appear first
- [ ] Two browser windows show alert status updates in real time without refresh
- [ ] Uploading a malformed CSV (missing MMSI column) returns a clear 422 error
- [ ] `pytest` passes with no regressions

---

## Sprint 4 — Enterprise Readiness (Post-Pilot)
**Timeline:** 4–8 weeks after first pilot signed | **Priority:** MEDIUM

These items are required for expansion beyond the first customer but can wait until
the pilot is signed and funded.

---

### Task 4.1 — Multi-tenancy: organisation isolation
**Files:** Schema, auth, all query layers

Add an `Organisation` model. Every `User`, `Alert`, `WatchlistEntry`, `ITDAEZone`, and
`AuditLog` record gets an `organisation_id` FK. All queries must be scoped to the current
user's organisation. Add a `super_admin` role for the AegisAIS platform operator that
can view across organisations.

---

### Task 4.2 — Satellite AIS integration (S-AIS)
**New module:** `apps/api/app/modules/sais/`

Integrate with a commercial satellite AIS provider (SpireGlobal, ORBCOMM, or exactEarth)
via their REST or streaming API. This fills the coverage gap for open-ocean vessel tracking
and is required for monitoring vessels operating outside terrestrial AIS range.

---

### Task 4.3 — Automated report generation
**New module:** `apps/api/app/modules/reports/`

Add `POST /v1/reports/generate` endpoint: accepts a time range, zone filter, and vessel
filter, and returns a PDF report (using `reportlab` or `weasyprint`) summarising alert
activity, top-risk vessels, and infrastructure zone incidents. Required for the "commander
briefing" use case documented in the Confluence roadmap.

---

### Task 4.4 — Password reset and email verification
**Files:** Auth module, new email integration

Add forgot-password and email verification flows. Required for onboarding non-admin users
at enterprise customers without the platform operator manually setting passwords.

---

### Task 4.5 — Role expansion: `analyst` vs `viewer` permissions
**Files:** Auth models, dependencies, all route handlers

Currently roles are `admin`, `viewer`, `analyst`. Enforce meaningful permission differences:
- `viewer`: read-only (can view alerts and map, cannot annotate or manage watchlist)
- `analyst`: can annotate alerts, manage watchlist, acknowledge/resolve
- `admin`: full access including zone management, user management, report generation

---

## Appendix A — File Reference Map

| File | Sprint | Task | Change Type |
|---|---|---|---|
| `apps/api/app/core/config.py` | 1, 2 | 1.1, 1.2, 1.5, 1.7, 2.1, 2.3 | Modify |
| `apps/api/app/modules/auth/service.py` | 1 | 1.2, 1.3 | Modify |
| `apps/api/app/modules/auth/dependencies.py` | 1 | 1.3 | Modify |
| `apps/api/app/modules/auth/api/routes_auth.py` | 1 | 1.2, 1.3 | Modify |
| `apps/api/app/modules/auth/models.py` | 1 | 1.2, 1.10 | Modify |
| `apps/api/app/main.py` | 1 | 1.7, 1.8 | Modify |
| `apps/api/app/infrastructure/ws/manager.py` | 1 | 1.6 | Modify |
| `apps/api/app/middleware/rate_limit.py` | 1 | 1.9 | Modify |
| `apps/api/app/middleware/security_headers.py` | 1 | 1.8 | **Create** |
| `apps/api/app/core/database.py` | 2 | 2.1 | Modify |
| `apps/api/app/services/workers/processing_worker.py` | 2 | 2.3 | Modify |
| `apps/api/app/services/workers/persistence_worker.py` | 2 | 2.3 | Modify |
| `apps/api/app/services/workers/alert_worker.py` | 2 | 2.3 | Modify |
| `apps/api/app/api/v1/upload.py` | 3 | 3.5 | Modify |
| `apps/api/app/modules/itdae/geofences/checker.py` | 3 | 3.1 | Modify |
| `apps/api/app/modules/itdae/models.py` | 3 | 3.1 | Modify/Create |
| `apps/api/app/modules/itdae/api/routes_itdae.py` | 3 | 3.1 | Modify |
| `apps/api/app/modules/vessels/models.py` | 3 | 3.3 | Modify |
| `apps/api/app/modules/vessels/api/routes_vessels.py` | 3 | 3.3 | Modify |
| `apps/api/app/modules/alerts/service.py` | 3 | 3.4 | Modify |
| `apps/api/.env.example` | 2 | 2.6 | **Create** |
| `infra/docker/docker-compose.yml` | 1, 2 | 1.4, 1.5, 2.2, 2.4, 2.5 | Modify |
| `infra/docker/nginx/nginx.conf` | 1 | 1.4 | **Create** |
| `infra/docker/backup/backup.sh` | 2 | 2.4 | **Create** |
| `infra/monitoring/prometheus.yml` | 2 | 2.5 | **Create** |
| `infra/monitoring/alert_rules.yml` | 2 | 2.5 | **Create** |
| `apps/web/src/features/itdae/components/ZoneManager.tsx` | 3 | 3.2 | **Create** |
| `apps/web/src/features/itdae/hooks/useZones.ts` | 3 | 3.2 | **Create** |
| `apps/web/src/features/vessels/components/WatchlistPanel.tsx` | 3 | 3.3 | **Create** |
| `apps/web/src/core/ws-url.ts` | 1 | 1.6 | Modify |

---

## Appendix B — Alembic Migrations Required

Run these in order after completing the relevant tasks:

```bash
cd apps/api

# After Task 1.2
alembic revision --autogenerate -m "add_refresh_tokens"
alembic upgrade head

# After Task 1.10
alembic revision --autogenerate -m "add_user_timestamps"
alembic upgrade head

# After Task 3.1
alembic revision --autogenerate -m "add_itdae_zones_table"
alembic upgrade head

# After Task 3.3
alembic revision --autogenerate -m "add_watchlist"
alembic upgrade head
```

---

## Appendix C — New Python Dependencies Required

Add to `apps/api/pyproject.toml` `[project.dependencies]`:

```toml
# Sprint 1
"bcrypt==4.3.0",       # already via passlib but pin explicitly
"cryptography>=43.0",  # for JWT JWK support (python-jose dependency, pin for CVE hygiene)

# Sprint 3 (reports — Task 4.3, post-pilot)
# "reportlab==4.2.5",  # uncomment when implementing PDF reports
```

---

## Appendix D — Cursor Prompt Templates

Use these verbatim prompts in **Cursor Composer Agent mode** for each task.

### Prompt for Task 1.1
```
Working in /Users/yusaf/aegisais/.

In apps/api/app/core/config.py:
1. Add an `app_env: str = "development"` field to the Settings class, sourced from the
   APP_ENV environment variable.
2. Add a @field_validator for `secret_key` that raises ValueError if the value is
   "supersecretkey" or shorter than 32 characters when app_env is "production".
3. After the `settings = Settings()` line, add a module-level `validate_production_config()`
   function that raises RuntimeError with a clear message if secret_key is the default
   value AND app_env is "production". Call it immediately after it is defined.
4. Create apps/api/.env.example with all environment variables used in the Settings class,
   grouped by category with comments. Mark required fields clearly.

Do not change any detection threshold defaults. Run the existing pytest suite and confirm
it still passes after your changes.
```

### Prompt for Task 1.2
```
Working in /Users/yusaf/aegisais/.

Implement JWT refresh token flow:

1. In apps/api/app/core/config.py: change access_token_expire_minutes default to 60.
   Add refresh_token_expire_days: int = 7.

2. In apps/api/app/modules/auth/models.py: add a RefreshToken SQLAlchemy model with fields:
   id (Integer PK), token_hash (String unique indexed — SHA-256 of raw token),
   user_id (Integer FK → users.id), expires_at (DateTime timezone=True),
   revoked (Boolean default False), created_at (DateTime timezone=True server_default now).

3. In apps/api/app/modules/auth/service.py:
   - Add create_refresh_token(user_id: int, db: Session) -> str
   - Add verify_refresh_token(raw_token: str, db: Session) -> Optional[User]
   - Add revoke_refresh_token(raw_token: str, db: Session) -> bool
   Use secrets.token_urlsafe(64) for the raw token. Store SHA-256 hash.

4. In apps/api/app/modules/auth/api/routes_auth.py:
   - Update POST /login to return both access_token and refresh_token.
     Set refresh_token as an HttpOnly Secure SameSite=Strict cookie.
   - Add POST /refresh: reads refresh token from cookie or request body,
     calls verify_refresh_token, issues new access token.
   - Add POST /logout: revokes both tokens, clears cookie.

5. Generate the Alembic migration:
   cd apps/api && alembic revision --autogenerate -m "add_refresh_tokens"

Run pytest and confirm all existing tests pass. Add tests for the new endpoints.
```

### Prompt for Task 1.4
```
Working in /Users/yusaf/aegisais/.

Add nginx reverse proxy with TLS termination to the Docker Compose setup:

1. Create infra/docker/nginx/nginx.conf with:
   - HTTP (port 80) → HTTPS redirect
   - HTTPS (port 443) termination with cert paths: /etc/nginx/certs/cert.pem and key.pem
   - proxy_pass to http://api:8000 for all traffic
   - Security headers: Strict-Transport-Security, X-Content-Type-Options, X-Frame-Options,
     X-XSS-Protection, Referrer-Policy
   - WebSocket upgrade support for /v1/stream path

2. Update infra/docker/docker-compose.yml:
   - Add nginx service using nginx:1.27-alpine, ports 80:80 and 443:443,
     mounting the nginx.conf and a ./nginx/certs volume
   - Remove direct port 8000:8000 mapping from the api service
   - api service should be reachable internally on port 8000 but not externally

3. Create infra/docker/nginx/README.md with:
   - Command to generate a self-signed cert for development
   - Instructions for Let's Encrypt / Certbot for production

Do not break the existing docker-compose services.
```

### Prompt for Task 2.2
```
Working in /Users/yusaf/aegisais/.

Update infra/docker/docker-compose.yml to add Docker health checks and restart policies
to all services:

- db (postgres): pg_isready health check, restart: unless-stopped
- redis: redis-cli ping health check (using REDIS_PASSWORD env var), restart: unless-stopped
- api: curl /v1/health health check with start_period: 20s, restart: unless-stopped,
  depends_on db and redis with condition: service_healthy
- processing-worker, persistence-worker, alert-worker, itdae-ingestion:
  restart: unless-stopped, depends_on db and redis with condition: service_healthy

Keep all existing environment variables and volume mounts unchanged.
```

### Prompt for Task 3.1
```
Working in /Users/yusaf/aegisais/.

Replace the hardcoded BALTIC_CABLE_ZONES in apps/api/app/modules/itdae/geofences/baltic_cables.py
with a database-driven zone management system:

1. Add an ITDAEZone SQLAlchemy model to apps/api/app/modules/itdae/models.py with fields:
   id, name (String unique), description (String), risk_level (String: low/medium/high/critical),
   polygon_geojson (JSON — GeoJSON Polygon), is_active (Boolean default True),
   created_by_id (Integer FK → users.id nullable), created_at, updated_at

2. Create a seeder function that reads BALTIC_CABLE_ZONES and inserts them into the DB
   on first startup (idempotent — check by name before inserting).
   Call it from apps/api/app/core/startup.py lifespan event.

3. Add CRUD endpoints to apps/api/app/modules/itdae/api/routes_itdae.py:
   GET /api/v1/itdae/zones (analyst), POST (admin), GET /{id} (analyst),
   PATCH /{id} (admin), DELETE /{id} admin — soft delete sets is_active=False

4. Update apps/api/app/modules/itdae/geofences/checker.py:
   get_zone_for_position and get_all_zones_for_position now accept zones: list[dict]
   as a parameter instead of importing BALTIC_CABLE_ZONES directly.
   Add a Redis cache layer for the zone list (TTL 300s, key aegisais:itdae_zones).

5. Generate migration: alembic revision --autogenerate -m "add_itdae_zones_table"

Run pytest and confirm all ITDAE tests pass. Add tests for the new CRUD endpoints.
```

---

*End of implementation plan. Total estimated engineering effort: Sprint 1 (2–3 weeks),
Sprint 2 (1–2 weeks), Sprint 3 (2–4 weeks), Sprint 4 (4–8 weeks post-pilot).*

*Generated from Seed fundraising package analysis — AegisAIS v0.1.0*
