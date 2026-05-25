from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.medical_agent import medical_agent
from app.api.auth import get_current_user
from app.db.database import async_session, get_db
from app.models.report import Report
from app.models.user import User
from app.schemas.chat import ChatHistoryResponse, ChatMessage, ChatRequest, ChatResponse
from app.schemas.report import CompareReportsRequest, CompareReportsResponse, ReportResponse, TimelineResponse
from app.services.gemini_service import gemini_service
from app.services.redis_service import redis_service
from app.models.medical_history import MedicalHistory
from app.models.medicine import Medicine

router = APIRouter(tags=["reports"])


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Report).where(Report.id == report_id, Report.user_id == current_user.id))
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/reports/compare", response_model=CompareReportsResponse)
async def compare_reports(
    data: CompareReportsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result_a = await db.execute(select(Report).where(Report.id == data.report_id_a, Report.user_id == current_user.id))
    result_b = await db.execute(select(Report).where(Report.id == data.report_id_b, Report.user_id == current_user.id))
    report_a = result_a.scalar_one_or_none()
    report_b = result_b.scalar_one_or_none()
    if not report_a or not report_b:
        raise HTTPException(status_code=404, detail="One or both reports not found")

    comparison = await gemini_service.compare_reports(
        {"title": report_a.title, "ai_summary": report_a.ai_summary, "ai_findings": report_a.ai_findings,
         "conditions": report_a.conditions, "medicines": report_a.medicines},
        {"title": report_b.title, "ai_summary": report_b.ai_summary, "ai_findings": report_b.ai_findings,
         "conditions": report_b.conditions, "medicines": report_b.medicines},
    )
    return CompareReportsResponse(report_a=report_a, report_b=report_b, comparison=comparison)


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    events_result = await db.execute(
        select(MedicalHistory)
        .where(MedicalHistory.user_id == current_user.id)
        .order_by(MedicalHistory.event_date.desc())
    )
    events = events_result.scalars().all()

    meds_result = await db.execute(
        select(Medicine).where(Medicine.user_id == current_user.id, Medicine.is_active == True)
    )
    medicines = [{"name": m.name, "dosage": m.dosage, "frequency": m.frequency} for m in meds_result.scalars().all()]

    conditions: set[str] = set()
    for e in events:
        if e.conditions:
            conditions.update(e.conditions)

    return TimelineResponse(events=events, medicines=medicines, conditions=list(conditions))


@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await medical_agent.chat(db, current_user.id, data.message, data.session_id, data.report_id)
    return ChatResponse(**result)


@router.get("/chat/{session_id}", response_model=ChatHistoryResponse)
async def chat_history(session_id: str, current_user: Annotated[User, Depends(get_current_user)]):
    messages = await redis_service.get_session_messages(session_id)
    return ChatHistoryResponse(
        session_id=session_id,
        messages=[ChatMessage(role=m["role"], content=m["content"]) for m in messages],
    )


@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            user_id = data.get("user_id")
            if not message or not user_id:
                continue

            async with async_session() as db:
                result = await medical_agent.chat(db, int(user_id), message, session_id)
                await db.commit()

            words = result["message"].split(" ")
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                await websocket.send_json({"type": "stream", "content": chunk})
            await websocket.send_json({"type": "done", "session_id": session_id})
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/report/{report_id}")
async def websocket_report_status(websocket: WebSocket, report_id: int):
    await websocket.accept()
    try:
        status_data = await redis_service.get_report_status(report_id)
        if status_data:
            await websocket.send_json(status_data)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
