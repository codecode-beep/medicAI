import logging
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.medical_history import MedicalHistory
from app.models.medicine import Medicine
from app.models.report import Report
from app.models.uploaded_file import UploadedFile
from app.rag.pipeline import rag_pipeline
from app.services.gemini_service import gemini_service
from app.services.pdf_service import extract_text_from_pdf
from app.services.redis_service import redis_service
from app.services.report_service import generate_medical_report_pdf
from app.services.s3_service import s3_service
from app.utils.auth import chunk_text, compute_file_hash

logger = logging.getLogger("medintel")

IMAGE_TYPES = {"image/jpeg", "image/png", "image/jpg", "image/webp", "image/tiff", "image/bmp"}
PDF_TYPES = {"application/pdf"}

PLACEHOLDER_MARKERS = (
    "Configure Gemini",
    "Configure GEMINI",
    "AI analysis unavailable",
    "quota exceeded",
)


def _is_placeholder_report(report: Report) -> bool:
    text = f"{report.ai_summary or ''} {report.ai_findings or ''} {report.recommendations or ''}"
    return any(marker in text for marker in PLACEHOLDER_MARKERS)


class MedicalAnalysisAgent:
    async def process_upload(
        self,
        db: AsyncSession,
        user_id: int,
        content: bytes,
        filename: str,
        mime_type: str,
        save_to_history: bool,
        question: str | None = None,
        patient_name: str = "Patient",
    ) -> dict[str, Any]:
        file_hash = compute_file_hash(content)
        file_type = "image" if mime_type in IMAGE_TYPES else "pdf" if mime_type in PDF_TYPES else "document"

        existing = await self._find_duplicate(db, file_hash, user_id)
        if existing:
            report = await self._get_report_for_file(db, existing.id)
            if report and report.status == "completed" and not _is_placeholder_report(report):
                message = "Duplicate file detected — reusing existing analysis."
                if save_to_history:
                    await self._apply_save_to_history(
                        db=db,
                        user_id=user_id,
                        report=report,
                        analysis=self._analysis_from_report(report),
                        extracted_text=existing.extracted_text or report.ai_summary or "",
                        patient_name=patient_name,
                        filename=filename or report.title,
                    )
                    message = "Duplicate file — added to your medical timeline."
                return {
                    "is_duplicate": True,
                    "file_id": existing.id,
                    "report_id": report.id,
                    "report": report,
                    "message": message,
                }
            if report:
                return await self._reanalyze_existing(
                    db=db,
                    user_id=user_id,
                    uploaded_file=existing,
                    report=report,
                    content=content,
                    mime_type=mime_type,
                    save_to_history=save_to_history,
                    question=question,
                    patient_name=patient_name,
                )

        s3_key, s3_url = s3_service.upload_file(content, filename, mime_type)

        uploaded_file = UploadedFile(
            user_id=user_id,
            file_hash=file_hash,
            original_filename=filename,
            file_type=file_type,
            mime_type=mime_type,
            s3_key=s3_key,
            s3_url=s3_url,
            file_size=len(content),
        )
        db.add(uploaded_file)
        await db.flush()

        report = Report(
            user_id=user_id,
            uploaded_file_id=uploaded_file.id,
            title=filename,
            report_type=file_type,
            status="processing",
            is_saved=save_to_history,
        )
        db.add(report)
        await db.flush()
        await redis_service.set_report_status(report.id, "processing")

        analysis, extracted_text, rag_context = await self._analyze_content(
            db, content, mime_type, file_type, user_id, uploaded_file, exclude_report_id=report.id
        )
        await self._fill_report(
            db, report, uploaded_file, analysis, extracted_text, user_id,
            save_to_history, patient_name, filename,
        )

        answer = None
        if question:
            answer = await gemini_service.chat(question, rag_context=rag_context)

        return {
            "is_duplicate": False,
            "file_id": uploaded_file.id,
            "report_id": report.id,
            "report": report,
            "analysis": analysis,
            "answer": answer,
            "message": "Analysis complete.",
        }

    async def _reanalyze_existing(
        self,
        db: AsyncSession,
        user_id: int,
        uploaded_file: UploadedFile,
        report: Report,
        content: bytes,
        mime_type: str,
        save_to_history: bool,
        question: str | None,
        patient_name: str,
    ) -> dict[str, Any]:
        file_type = uploaded_file.file_type
        report.status = "processing"
        report.is_saved = save_to_history
        await redis_service.set_report_status(report.id, "processing")

        analysis, extracted_text, rag_context = await self._analyze_content(
            db, content, mime_type, file_type, user_id, uploaded_file, exclude_report_id=report.id
        )
        await self._fill_report(
            db, report, uploaded_file, analysis, extracted_text, user_id,
            save_to_history, patient_name, report.title,
        )

        answer = None
        if question:
            answer = await gemini_service.chat(question, rag_context=rag_context)

        return {
            "is_duplicate": False,
            "file_id": uploaded_file.id,
            "report_id": report.id,
            "report": report,
            "analysis": analysis,
            "answer": answer,
            "message": "Report re-analyzed with AI.",
        }

    async def _analyze_content(
        self,
        db: AsyncSession,
        content: bytes,
        mime_type: str,
        file_type: str,
        user_id: int,
        uploaded_file: UploadedFile,
        exclude_report_id: int | None = None,
    ) -> tuple[dict[str, Any], str, str]:
        extracted_text = ""
        if file_type == "pdf":
            extracted_text = extract_text_from_pdf(content)
            uploaded_file.extracted_text = extracted_text
            analysis = await gemini_service.analyze_text(extracted_text)
        elif file_type == "image":
            analysis = await gemini_service.analyze_image(content, mime_type)
            extracted_text = analysis.get("summary", "")
            uploaded_file.extracted_text = extracted_text
        else:
            extracted_text = content.decode("utf-8", errors="ignore")
            uploaded_file.extracted_text = extracted_text
            analysis = await gemini_service.analyze_text(extracted_text)

        rag_context = await rag_pipeline.retrieve_context(extracted_text[:500], user_id)
        if rag_context:
            analysis["rag_context_used"] = True

        historical = await self._get_historical_comparison(
            db, user_id, analysis, exclude_report_id=exclude_report_id
        )
        analysis["historical_comparison"] = historical
        return analysis, extracted_text, rag_context

    async def _fill_report(
        self,
        db: AsyncSession,
        report: Report,
        uploaded_file: UploadedFile,
        analysis: dict[str, Any],
        extracted_text: str,
        user_id: int,
        save_to_history: bool,
        patient_name: str,
        filename: str,
    ) -> None:
        historical = analysis.get("historical_comparison", {})
        report.ai_summary = analysis.get("summary")
        report.ai_findings = {
            "findings": analysis.get("findings", []),
            "interpretation": analysis.get("interpretation", ""),
        }
        report.medicines = analysis.get("medicines", [])
        report.conditions = analysis.get("conditions", [])
        report.severity = analysis.get("severity")
        report.recommendations = analysis.get("recommendations", [])
        report.historical_comparison = historical
        report.status = "completed"
        report.is_saved = save_to_history

        if save_to_history:
            await self._apply_save_to_history(
                db=db,
                user_id=user_id,
                report=report,
                analysis=analysis,
                extracted_text=extracted_text,
                patient_name=patient_name,
                filename=filename,
            )

        await db.flush()
        await redis_service.set_report_status(report.id, "completed", {"report_id": report.id})

    async def _find_duplicate(self, db: AsyncSession, file_hash: str, user_id: int) -> UploadedFile | None:
        result = await db.execute(
            select(UploadedFile)
            .options(selectinload(UploadedFile.report))
            .where(UploadedFile.file_hash == file_hash, UploadedFile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def _get_report_for_file(self, db: AsyncSession, uploaded_file_id: int) -> Report | None:
        result = await db.execute(
            select(Report).where(Report.uploaded_file_id == uploaded_file_id)
        )
        return result.scalar_one_or_none()

    async def _get_historical_comparison(
        self,
        db: AsyncSession,
        user_id: int,
        current: dict,
        exclude_report_id: int | None = None,
    ) -> dict:
        query = (
            select(Report)
            .where(Report.user_id == user_id, Report.is_saved == True, Report.status == "completed")
            .order_by(Report.created_at.desc())
            .limit(2)
        )
        result = await db.execute(query)
        reports = [r for r in result.scalars().all() if r.id != exclude_report_id]
        prev = reports[0] if reports else None
        if not prev:
            return {"summary": "No previous reports for comparison."}
        prev_data = {
            "title": prev.title,
            "ai_summary": prev.ai_summary,
            "ai_findings": prev.ai_findings,
            "conditions": prev.conditions,
            "medicines": prev.medicines,
        }
        current_data = {
            "title": "Current Report",
            "ai_summary": current.get("summary"),
            "ai_findings": current.get("findings"),
            "conditions": current.get("conditions"),
            "medicines": current.get("medicines"),
        }
        return await gemini_service.compare_reports(prev_data, current_data)

    @staticmethod
    def _analysis_from_report(report: Report) -> dict[str, Any]:
        findings = report.ai_findings or {}
        return {
            "summary": report.ai_summary,
            "findings": findings.get("findings", []) if isinstance(findings, dict) else [],
            "interpretation": findings.get("interpretation", "") if isinstance(findings, dict) else "",
            "medicines": report.medicines or [],
            "conditions": report.conditions or [],
            "severity": report.severity,
            "recommendations": report.recommendations or [],
        }

    async def _has_history_entry(self, db: AsyncSession, report_id: int, user_id: int) -> bool:
        result = await db.execute(
            select(MedicalHistory.id).where(
                MedicalHistory.report_id == report_id,
                MedicalHistory.user_id == user_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def _apply_save_to_history(
        self,
        db: AsyncSession,
        user_id: int,
        report: Report,
        analysis: dict[str, Any],
        extracted_text: str,
        patient_name: str,
        filename: str,
    ) -> None:
        report.is_saved = True
        if await self._has_history_entry(db, report.id, user_id):
            return

        historical = report.historical_comparison or analysis.get("historical_comparison", {})
        if not report.generated_pdf_s3_key:
            pdf_bytes = generate_medical_report_pdf(
                patient_name, filename, analysis, historical, []
            )
            pdf_key, pdf_url = s3_service.upload_file(
                pdf_bytes, f"report_{report.id}.pdf", "application/pdf", folder="reports"
            )
            report.generated_pdf_s3_key = pdf_key
            report.generated_pdf_url = pdf_url

        await rag_pipeline.index_report(
            extracted_text or analysis.get("summary", "") or "", user_id, report.id
        )
        await self._update_medical_history(db, user_id, report, analysis)
        await self._update_medicines(db, user_id, report, analysis.get("medicines", []))

    async def backfill_medical_history(self, db: AsyncSession, user_id: int) -> None:
        """Create timeline rows for saved reports that predate the history fix."""
        history_report_ids = select(MedicalHistory.report_id).where(
            MedicalHistory.user_id == user_id,
            MedicalHistory.report_id.isnot(None),
        )
        result = await db.execute(
            select(Report).where(
                Report.user_id == user_id,
                Report.is_saved == True,
                Report.status == "completed",
                Report.id.not_in(history_report_ids),
            )
        )
        for report in result.scalars().all():
            await self._apply_save_to_history(
                db=db,
                user_id=user_id,
                report=report,
                analysis=self._analysis_from_report(report),
                extracted_text=report.ai_summary or "",
                patient_name="Patient",
                filename=report.title,
            )

    async def _update_medical_history(self, db: AsyncSession, user_id: int, report: Report, analysis: dict) -> None:
        if await self._has_history_entry(db, report.id, user_id):
            return
        entry = MedicalHistory(
            user_id=user_id,
            report_id=report.id,
            title=report.title,
            event_type=report.report_type,
            description=analysis.get("summary"),
            conditions=analysis.get("conditions"),
            medicines=analysis.get("medicines"),
            findings=report.ai_findings,
        )
        db.add(entry)

    async def _update_medicines(self, db: AsyncSession, user_id: int, report: Report, medicines: list) -> None:
        for med in medicines:
            if med.get("name"):
                db.add(Medicine(
                    user_id=user_id,
                    name=med["name"],
                    dosage=med.get("dosage"),
                    frequency=med.get("frequency"),
                    is_active=True,
                    source_report_id=report.id,
                ))

    async def chat(
        self,
        db: AsyncSession,
        user_id: int,
        message: str,
        session_id: str | None = None,
        report_id: int | None = None,
    ) -> dict[str, Any]:
        session_id = session_id or uuid4().hex
        history = await redis_service.get_session_messages(session_id)
        rag_context = await rag_pipeline.retrieve_context(message, user_id, report_id=report_id)

        if report_id:
            result = await db.execute(select(Report).where(Report.id == report_id, Report.user_id == user_id))
            report = result.scalar_one_or_none()
            if report:
                rag_context += f"\n\nCurrent report: {report.title}\nSummary: {report.ai_summary}"

        response = await gemini_service.chat(message, history, rag_context)
        await redis_service.add_message(session_id, "user", message)
        await redis_service.add_message(session_id, "assistant", response)

        from app.models.conversation import Conversation
        db.add(Conversation(user_id=user_id, session_id=session_id, role="user", content=message))
        db.add(Conversation(user_id=user_id, session_id=session_id, role="assistant", content=response))

        return {"session_id": session_id, "message": response, "role": "assistant"}


medical_agent = MedicalAnalysisAgent()
