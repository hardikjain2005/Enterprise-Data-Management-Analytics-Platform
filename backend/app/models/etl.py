from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    source_id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(String(80), unique=True)
    source_type: Mapped[str] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool]


class EtlJob(Base):
    __tablename__ = "etl_jobs"

    job_id: Mapped[int] = mapped_column(primary_key=True)
    job_name: Mapped[str] = mapped_column(String(80), unique=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.source_id"))
    source_file: Mapped[str] = mapped_column(String(120))
    target_table: Mapped[str] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool]

    source: Mapped[DataSource] = relationship()


class EtlExecutionLog(Base):
    __tablename__ = "etl_execution_logs"

    execution_id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("etl_jobs.job_id"))
    started_at: Mapped[datetime]
    ended_at: Mapped[datetime | None]
    records_read: Mapped[int]
    records_inserted: Mapped[int]
    records_updated: Mapped[int]
    records_rejected: Mapped[int]
    error_count: Mapped[int]
    status: Mapped[str] = mapped_column(String(20))
    error_message: Mapped[str | None] = mapped_column(String(1000))

    job: Mapped[EtlJob] = relationship()
