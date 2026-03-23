import logging
from pydantic_settings import BaseSettings
from pydantic import field_validator, ValidationInfo

_log = logging.getLogger("aegisais.config")


class Settings(BaseSettings):
    app_name: str = "AegisAIS"
    # development | test | staging | production | docker — production gate (IMPLEMENTATION_PLAN Sprint 1)
    app_env: str = "development"

    database_url: str = "sqlite:///./aegisais.db"  # default local
    # SQLAlchemy pool (PostgreSQL and other non-SQLite drivers; Sprint 2)
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    allow_replay: bool = True
    
    # Security settings
    secret_key: str = "supersecretkey"  # Change in production!
    # Comma-separated origins; env CORS_ALLOWED_ORIGINS
    cors_allowed_origins: str = (
        "http://localhost:5174,http://127.0.0.1:5174,"
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:3000"
    )
    # Optional explicit Redis password (compose may embed in REDIS_URL instead).
    redis_password: str = ""
    # When True, WebSocket /v1/stream requires ?token=<JWT> for an active user (Sprint 1 default: on).
    websocket_require_auth: bool = True
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    password_reset_token_ttl_hours: int = 1
    # Base URL for password reset links (query: ?token=...). Used in dev logs and SMTP emails.
    password_reset_link_base: str = "http://localhost:5174"
    # Optional SMTP for password reset emails; if SMTP_HOST is empty, dev logs link instead (see auth service).
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = ""

    # Multi-tenancy (Sprint 4): default org id for workers and backfilled data
    default_organisation_id: int = 1

    # Infrastructure settings
    redis_url: str = "redis://localhost:6379/0"
    redis_max_connections: int = 10
    redis_prefix: str = "aegisais"
    
    # Stream names
    stream_ais_raw: str = "ais_raw"
    stream_ais_processed: str = "ais_processed"
    stream_ais_alerts: str = "ais_alerts"
    
    # Persistence settings
    persistence_batch_size: int = 50
    persistence_flush_interval_sec: float = 1.0
    
    # Large dataset optimizations
    default_batch_size: int = 100  # Database commit batch size
    streaming_threshold_mb: float = 50.0  # Use streaming for files larger than this
    chunk_size: int = 10000  # CSV chunk size for streaming

    # Upload / ingest hardening (Sprint 3)
    max_decompressed_size_gb: float = 50.0
    scan_uploads_for_malware: bool = False  # TODO: integrate AV / malware scanning when True

    # Satellite AIS (S-AIS) — Sprint 4 stub; real HTTP when keys are configured (see app.modules.sais)
    SAIS_PROVIDER: str = "none"  # spire | orbcomm | exactearth | none
    SAIS_API_KEY: str = ""
    SAIS_API_BASE_URL: str = ""
    OPENSKY_API_BASE_URL: str = "https://opensky-network.org"
    OPENSKY_USERNAME: str = ""
    OPENSKY_PASSWORD: str = ""
    OPENSKY_RATE_LIMIT_PER_MINUTE: int = 60
    OPENSKY_RATE_LIMIT_PER_DAY: int = 4000
    OPENSKY_CACHE_TTL_SEC: int = 30

    # ITDAE Core Settings
    ITDAE_AIS_API_KEY: str = ""
    ITDAE_BALTIC_BBOX: str = ""
    ITDAE_GEOFENCE_BUFFER_NM: float = 5.0  # Buffer around cable corridors in nautical miles

    # Detection thresholds
    # TELEPORT rule thresholds (tiered by time gap)
    teleport_speed_knots_short: float = 60.0  # For dt <= 120s (Tier 1)
    teleport_speed_knots_medium: float = 100.0  # For 120s < dt <= 1800s (Tier 1)
    teleport_dt_short_max_sec: int = 120
    teleport_dt_medium_max_sec: int = 1800  # 30 minutes
    teleport_dt_long_max_sec: int = 3600  # 60 minutes (data gap only)

    # Tier-2 (suspicious) teleport thresholds
    teleport_suspicious_min_knots: float = 40.0  # lower bound for suspicious speed

    # TURN_RATE rule thresholds (Tier 1)
    max_turn_rate_deg_per_sec: float = 3.0
    max_turn_rate_high_speed_deg_per_sec: float = 20.0  # For HEADING/COG consistency check
    min_speed_for_turn_check_knots: float = 10.0  # Full severity
    min_speed_for_turn_check_low_knots: float = 3.0  # Reduced sensitivity
    turn_rate_dt_min_sec: float = 2.0  # Skip if dt < 2s (noise)

    # Tier-2 (suspicious) turn rate thresholds
    turn_rate_suspicious_min_deg_per_sec: float = 1.0

    # ACCELERATION rule thresholds
    max_accel_knots_per_sec: float = 5.0  # Max acceleration in knots/second
    sog_implied_speed_diff_threshold_knots: float = 20.0  # Difference between SOG and implied speed

    # POSITION_INVALID rule thresholds
    position_outlier_distance_km: float = 1000.0  # Max reasonable distance from previous point

    # Deduplication/cooldown
    alert_cooldown_sec: int = 300  # 5 minutes cooldown per (MMSI, rule_type)
    fused_cable_proximity_m: float = 1500.0
    fused_cable_time_window_sec: int = 1200

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str, info: ValidationInfo) -> str:
        env = (info.data or {}).get("app_env") or "development"
        low = v.strip().lower()
        if low.startswith("sqlite") and env not in ("development", "test", "production"):
            _log.warning(
                "DATABASE_URL uses SQLite while APP_ENV=%s; not recommended for production workloads",
                env,
            )
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info: ValidationInfo) -> str:
        env = (info.data or {}).get("app_env") or "development"
        if env == "production":
            if v == "supersecretkey" or len(v) < 32:
                raise ValueError(
                    "SECRET_KEY must be at least 32 characters and not the default when APP_ENV=production"
                )
        return v

    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allowed_origins.split(",") if o.strip()]

    @field_validator("teleport_speed_knots_short", "teleport_speed_knots_medium")
    @classmethod
    def validate_positive_speed(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Speed thresholds must be positive")
        if v > 1000:
            raise ValueError("Speed thresholds unreasonably high (>1000 knots)")
        return v

    @field_validator("teleport_dt_short_max_sec", "teleport_dt_medium_max_sec", "teleport_dt_long_max_sec")
    @classmethod
    def validate_time_gaps(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Time gaps must be positive")
        if v > 86400:  # 24 hours
            raise ValueError("Time gaps unreasonably large (>24 hours)")
        return v

    @field_validator("max_turn_rate_deg_per_sec", "max_turn_rate_high_speed_deg_per_sec")
    @classmethod
    def validate_turn_rates(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Turn rate thresholds must be positive")
        if v > 360:
            raise ValueError("Turn rate thresholds unreasonably high (>360 deg/s)")
        return v

    @field_validator("alert_cooldown_sec")
    @classmethod
    def validate_cooldown(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Cooldown must be non-negative")
        if v > 86400:  # 24 hours
            raise ValueError("Cooldown unreasonably large (>24 hours)")
        return v

    @field_validator("SAIS_PROVIDER")
    @classmethod
    def validate_sais_provider(cls, v: str) -> str:
        allowed = {"spire", "orbcomm", "exactearth", "none"}
        low = (v or "").strip().lower()
        if low not in allowed:
            raise ValueError(
                f"SAIS_PROVIDER must be one of {sorted(allowed)}; got {v!r}"
            )
        return low

    @field_validator("default_batch_size")
    @classmethod
    def validate_batch_size(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Batch size must be positive")
        if v > 100000:
            raise ValueError("Batch size unreasonably large (>100000)")
        return v

    # Rate limiting: use Redis sorted-set sliding window (shared across workers).
    # When False, uses in-process memory (fine for dev/tests; single worker only).
    rate_limit_use_redis: bool = False

    # Audit Logging
    enable_audit_logging: bool = True
    audit_log_retention_days: int = 90
    
    # Security & Interoperability
    strict_schema_validation: bool = True
    enable_telemetry_scrubbing: bool = True
    
    model_config = {
        "env_prefix": "",
        "env_file": ".env",
        "extra": "ignore"
    }

settings = Settings()


def validate_production_config() -> None:
    """Fail fast on insecure defaults when APP_ENV=production (Sprint 1)."""
    if settings.app_env != "production":
        return
    if settings.secret_key == "supersecretkey" or len(settings.secret_key) < 32:
        raise RuntimeError(
            "SECRET_KEY must be set to a strong value (>=32 chars, not the default) when APP_ENV=production"
        )
    if not settings.websocket_require_auth:
        raise RuntimeError(
            "WEBSOCKET_REQUIRE_AUTH must be true when APP_ENV=production"
        )
    if settings.database_url.lower().startswith("sqlite"):
        raise RuntimeError(
            "DATABASE_URL cannot use SQLite when APP_ENV=production; use PostgreSQL"
        )


validate_production_config()
