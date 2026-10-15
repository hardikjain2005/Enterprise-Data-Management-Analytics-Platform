from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuditLog
from .common import paginate


def list_audit_logs(db: Session, table: str | None, action: str | None, record_id: int | None,
                    changed_by: str | None, page: int, page_size: int) -> dict:
    query = select(AuditLog)
    if table:
        query = query.where(AuditLog.table_name == table)
    if action:
        query = query.where(AuditLog.action == action)
    if record_id:
        query = query.where(AuditLog.record_id == record_id)
    if changed_by:
        query = query.where(AuditLog.changed_by == changed_by)
    query = query.order_by(AuditLog.changed_at.desc(), AuditLog.audit_id.desc())
    return paginate(db, query, page, page_size)
