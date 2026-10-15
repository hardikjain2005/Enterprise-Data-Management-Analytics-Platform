from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.common import Page
from ..schemas.data_quality import DataQualityIssueOut, DataQualitySummary, IssueResolution, QualityCheckResult
from ..services import data_quality as service

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


@router.get("/issues", response_model=Page[DataQualityIssueOut])
def list_issues(
    status: Literal["OPEN", "RESOLVED", "IGNORED"] | None = None,
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None,
    table: str | None = None,
    issue_type: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.list_issues(db, status, severity, table, issue_type, search, page, page_size)


@router.get("/summary", response_model=DataQualitySummary)
def summary(db: Session = Depends(get_db)):
    return service.summary(db)


@router.post("/run-checks", response_model=QualityCheckResult)
def run_checks(db: Session = Depends(get_db)):
    """Runs the stored procedure sp_run_data_quality_checks."""
    return service.run_checks(db)


@router.patch("/issues/{issue_id}", response_model=DataQualityIssueOut)
def resolve_issue(issue_id: int, body: IssueResolution, db: Session = Depends(get_db)):
    return service.resolve_issue(db, issue_id, body.resolution_status, body.resolution_note)
