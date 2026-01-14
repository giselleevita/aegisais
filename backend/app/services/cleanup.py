"""Cleanup tasks for database maintenance."""
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from ..models import AlertCooldown
from ..settings import settings

log = logging.getLogger("aegisais.cleanup")


def cleanup_old_cooldowns(db: Session, max_age_days: int = 7) -> int:
    """
    Remove cooldown records older than max_age_days.
    
    Args:
        db: Database session
        max_age_days: Maximum age in days for cooldown records (default: 7)
    
    Returns:
        Number of records deleted
    """
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    
    try:
        deleted = db.query(AlertCooldown).filter(
            AlertCooldown.last_alert_timestamp < cutoff_date
        ).delete()
        
        db.commit()
        log.info("Cleaned up %d old cooldown records (older than %d days)", deleted, max_age_days)
        return deleted
    except Exception as e:
        log.error("Error cleaning up cooldown records: %s", e, exc_info=True)
        db.rollback()
        raise
