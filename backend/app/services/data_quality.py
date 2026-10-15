from datetime import datetime

from fastapi import HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from ..models import DataQualityIssue, DataSource
from .common import paginate


def list_issues(db: Session, status: str | None, severity: str | None, table: str | None,
                issue_type: str | None, search: str | None, page: int, page_size: int) -> dict:
    query = (
        select(*[c for c in DataQualityIssue.__table__.columns if c.name != "source_id"],
               DataSource.source_name)
        .outerjoin(DataSource, DataSource.source_id == DataQualityIssue.source_id)
    )
    if status:
        query = query.where(DataQualityIssue.resolution_status == status)
    if severity:
        query = query.where(DataQualityIssue.severity == severity)
    if table:
        query = query.where(DataQualityIssue.table_name == table)
    if issue_type:
        query = query.where(DataQualityIssue.issue_type == issue_type)
    if search:
        query = query.where(DataQualityIssue.description.like(f"%{search}%")
                            | DataQualityIssue.record_identifier.like(f"%{search}%"))
    severity_order = func.field(DataQualityIssue.severity, "CRITICAL", "HIGH", "MEDIUM", "LOW")
    query = query.order_by(DataQualityIssue.detected_at.desc(), severity_order, DataQualityIssue.issue_id)
    return paginate(db, query, page, page_size)


def _counts(db: Session, column, only_open: bool = True) -> list[dict]:
    query = select(column.label("label"), func.count().label("count")).group_by(column)
    if only_open:
        query = query.where(DataQualityIssue.resolution_status == "OPEN")
    return [dict(r) for r in db.execute(query.order_by(func.count().desc())).mappings()]


def summary(db: Session) -> dict:
    return {
        "total_issues": db.scalar(select(func.count()).select_from(DataQualityIssue)),
        "open_issues": db.scalar(select(func.count()).where(DataQualityIssue.resolution_status == "OPEN")),
        "by_severity": _counts(db, DataQualityIssue.severity),
        "by_type": _counts(db, DataQualityIssue.issue_type),
        "by_table": _counts(db, DataQualityIssue.table_name),
        "by_rule": _counts(db, DataQualityIssue.rule_name),
    }


def run_checks(db: Session) -> dict:
    db.execute(text("CALL sp_run_data_quality_checks(@found)"))
    found = db.execute(text("SELECT @found")).scalar()
    db.commit()
    return {"new_issues_found": found or 0}


def resolve_issue(db: Session, issue_id: int, status: str, note: str | None) -> dict:
    issue = db.get(DataQualityIssue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    issue.resolution_status = status
    issue.resolution_note = note
    issue.resolved_at = None if status == "OPEN" else datetime.now()   # CHECK constraint requires this
    db.commit()
    return {
        **{c.name: getattr(issue, c.name) for c in DataQualityIssue.__table__.columns},
        "source_name": issue.source.source_name if issue.source else None,
    }
