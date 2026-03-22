from app.modules.audit.models import AuditLog
from app.modules.audit.schemas import AuditLogOut


def audit_log_to_out(row: AuditLog) -> AuditLogOut:
    return AuditLogOut.model_validate(row, from_attributes=True)
