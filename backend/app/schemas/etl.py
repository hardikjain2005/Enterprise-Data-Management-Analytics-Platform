from datetime import datetime

from .common import ORMModel


class EtlJobStatus(ORMModel):
    job_id: int
    job_name: str
    source_name: str
    source_file: str
    target_table: str
    total_runs: int
    failed_runs: int
    last_execution_id: int | None
    last_started_at: datetime | None
    last_ended_at: datetime | None
    last_status: str | None
    last_records_read: int | None
    last_records_inserted: int | None
    last_records_updated: int | None
    last_records_rejected: int | None


class EtlLog(ORMModel):
    execution_id: int
    job_id: int
    job_name: str
    started_at: datetime
    ended_at: datetime | None
    duration_ms: int | None
    records_read: int
    records_inserted: int
    records_updated: int
    records_rejected: int
    error_count: int
    status: str
    error_message: str | None
