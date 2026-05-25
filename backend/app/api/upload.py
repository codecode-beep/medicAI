from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.medical_agent import medical_agent
from app.api.auth import get_current_user
from app.db.database import get_db
from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportListResponse, ReportResponse, UploadResponse

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/analyze", response_model=UploadResponse)
async def analyze_file(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    save_to_history: bool = Form(False),
    question: str | None = Form(None),
):
    content = await file.read()
    result = await medical_agent.process_upload(
        db=db,
        user_id=current_user.id,
        content=content,
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        save_to_history=save_to_history,
        question=question,
        patient_name=current_user.full_name,
    )
    return UploadResponse(
        file_id=result.get("file_id"),
        report_id=result.get("report_id"),
        is_duplicate=result.get("is_duplicate", False),
        message=result.get("message", "Processing complete"),
        status="completed",
    )


@router.get("/reports", response_model=ReportListResponse)
async def list_reports(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 20,
    saved_only: bool = Query(False),
):
    filters = [Report.user_id == current_user.id, Report.status == "completed"]
    if saved_only:
        filters.append(Report.is_saved == True)

    count_result = await db.execute(
        select(func.count()).select_from(Report).where(*filters)
    )
    total = count_result.scalar() or 0
    result = await db.execute(
        select(Report)
        .where(*filters)
        .order_by(Report.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    reports = result.scalars().all()
    return ReportListResponse(reports=reports, total=total)
