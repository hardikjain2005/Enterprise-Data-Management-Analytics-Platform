from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.common import Page
from ..schemas.etl import EtlJobStatus, EtlLog
from ..services import etl as service

router = APIRouter(prefix="/etl", tags=["ETL Monitoring"])


@router.get("/jobs", response_model=list[EtlJobStatus])
def list_jobs(db: Session = Depends(get_db)):
    """Every ETL job with its latest run (view vw_etl_job_status)."""
    return service.list_jobs(db)


@router.get("/logs", response_model=Page[EtlLog])
def list_logs(
    job_id: int | None = None,
    status: Literal["RUNNING", "SUCCESS", "PARTIAL_SUCCESS", "FAILED"] | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return service.list_logs(db, job_id, status, page, page_size)
