from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .etl import DataSource


class DataQualityIssue(Base):
    __tablename__ = "data_quality_issues"

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int | None] = mapped_column(ForeignKey("etl_execution_logs.execution_id"))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.source_id"))
    table_name: Mapped[str] = mapped_column(String(64))
    record_identifier: Mapped[str | None] = mapped_column(String(100))
    column_name: Mapped[str | None] = mapped_column(String(64))
    rule_name: Mapped[str] = mapped_column(String(60))
    issue_type: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(500))
    severity: Mapped[str] = mapped_column(String(10))
    detected_at: Mapped[datetime]
    resolution_status: Mapped[str] = mapped_column(String(20))
    resolved_at: Mapped[datetime | None]
    resolution_note: Mapped[str | None] = mapped_column(String(255))

    source: Mapped[DataSource | None] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_logs"

    audit_id: Mapped[int] = mapped_column(primary_key=True)
    table_name: Mapped[str] = mapped_column(String(64))
    record_id: Mapped[int]
    action: Mapped[str] = mapped_column(String(10))
    old_values: Mapped[dict | None] = mapped_column(JSON)
    new_values: Mapped[dict | None] = mapped_column(JSON)
    changed_by: Mapped[str] = mapped_column(String(100))
    changed_at: Mapped[datetime]
