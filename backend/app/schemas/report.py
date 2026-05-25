from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    file_id: int | None = None
    report_id: int | None = None
    is_duplicate: bool = False
    message: str
    status: str = "processing"


class ReportCreate(BaseModel):
    title: str | None = None
    save_to_history: bool = True


class ReportResponse(BaseModel):
    id: int
    user_id: int
    uploaded_file_id: int | None
    title: str
    report_type: str
    status: str
    ai_summary: str | None
    ai_findings: dict | None
    medicines: list | None
    conditions: list | None
    severity: str | None
    recommendations: list | None
    historical_comparison: dict | None
    generated_pdf_url: str | None
    is_saved: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportListResponse(BaseModel):
    reports: list[ReportResponse]
    total: int


class CompareReportsRequest(BaseModel):
    report_id_a: int
    report_id_b: int


class CompareReportsResponse(BaseModel):
    report_a: ReportResponse
    report_b: ReportResponse
    comparison: dict[str, Any]


class TimelineEvent(BaseModel):
    id: int
    title: str
    event_type: str
    description: str | None
    conditions: list | None
    medicines: list | None
    findings: dict | None
    event_date: datetime
    report_id: int | None

    model_config = {"from_attributes": True}


class TimelineResponse(BaseModel):
    events: list[TimelineEvent]
    medicines: list[dict[str, Any]]
    conditions: list[str]


class AnalysisRequest(BaseModel):
    question: str | None = None
    save_to_history: bool = False
    session_id: str | None = None
