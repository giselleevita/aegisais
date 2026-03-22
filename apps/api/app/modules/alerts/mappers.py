"""Map ORM rows to API DTOs without leaking __dict__ coupling."""
from app.modules.alerts.models import Alert
from app.modules.alerts.schemas import AlertOut


def alert_to_out(alert: Alert) -> AlertOut:
    return AlertOut.model_validate(alert, from_attributes=True)
