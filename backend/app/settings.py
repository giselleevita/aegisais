from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "AegisAIS"
    database_url: str = "sqlite:///./aegisais.db"  # default local
    allow_replay: bool = True
    
    # Large dataset optimizations
    default_batch_size: int = 100  # Database commit batch size
    streaming_threshold_mb: float = 50.0  # Use streaming for files larger than this
    chunk_size: int = 10000  # CSV chunk size for streaming

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

    class Config:
        env_prefix = ""
        env_file = ".env"

settings = Settings()
