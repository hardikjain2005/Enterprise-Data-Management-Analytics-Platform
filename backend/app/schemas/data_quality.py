from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from .common import ORMModel


class DataQualityIssueOut(ORMModel):
    issue_id: int
    execution_id: int | None
    source_name: str | None
    table_name: str
    record_identifier: str | None
    column_name: str | None
    rule_name: str
    issue_type: str
    description: str
    severity: str
    detected_at: datetime
    resolution_status: str
    resolved_at: datetime | None
    resolution_note: str | None


class IssueResolution(BaseModel):
    resolution_status: Literal["OPEN", "RESOLVED", "IGNORED"]
    resolution_note: str | None = Field(default=None, max_length=255)


class CountItem(BaseModel):
    label: str
    count: int


class DataQualitySummary(BaseModel):
    total_issues: int
    open_issues: int
    by_severity: list[CountItem]
    by_type: list[CountItem]
    by_table: list[CountItem]
    by_rule: list[CountItem]


class QualityCheckResult(BaseModel):
    new_issues_found: int
