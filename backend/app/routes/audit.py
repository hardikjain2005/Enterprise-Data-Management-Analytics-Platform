from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.audit import AuditLogOut
from ..schemas.common import Page
from ..services import audit as service

router = APIRouter(prefix="/audit-logs", tags=["Audit"])


@router.get("", response_model=Page[AuditLogOut])
def list_audit_logs(
    table: Literal["customers", "products", "orders", "payments"] | None = None,
    action: Literal["INSERT", "UPDATE", "DELETE"] | None = None,
    record_id: int | None = None,
    changed_by: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.list_audit_logs(db, table, action, record_id, changed_by, page, page_size)
