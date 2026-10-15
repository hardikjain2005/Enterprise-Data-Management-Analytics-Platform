from datetime import datetime

from .common import ORMModel


class AuditLogOut(ORMModel):
    audit_id: int
    table_name: str
    record_id: int
    action: str
    old_values: dict | None
    new_values: dict | None
    changed_by: str
    changed_at: datetime
