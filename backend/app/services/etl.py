from sqlalchemy import select, text
from sqlalchemy.orm import Session

from ..models import EtlExecutionLog, EtlJob
from .common import paginate


def list_jobs(db: Session) -> list[dict]:
    return [dict(r) for r in db.execute(text("SELECT * FROM vw_etl_job_status ORDER BY job_id")).mappings()]


def list_logs(db: Session, job_id: int | None, status: str | None, page: int, page_size: int) -> dict:
    query = (
        select(*EtlExecutionLog.__table__.columns, EtlJob.job_name)
        .join(EtlJob, EtlJob.job_id == EtlExecutionLog.job_id)
    )
    if job_id:
        query = query.where(EtlExecutionLog.job_id == job_id)
    if status:
        query = query.where(EtlExecutionLog.status == status)
    query = query.order_by(EtlExecutionLog.started_at.desc(), EtlExecutionLog.execution_id.desc())
    result = paginate(db, query, page, page_size)
    for log in result["items"]:
        ended, started = log["ended_at"], log["started_at"]
        log["duration_ms"] = int((ended - started).total_seconds() * 1000) if ended else None
    return result
