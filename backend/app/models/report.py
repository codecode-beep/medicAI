from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    uploaded_file_id: Mapped[int | None] = mapped_column(ForeignKey("uploaded_files.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_findings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    medicines: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    conditions: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    recommendations: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    historical_comparison: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    generated_pdf_s3_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    generated_pdf_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    is_saved: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="reports")
    uploaded_file = relationship("UploadedFile", back_populates="report")
    medical_history_entries = relationship("MedicalHistory", back_populates="report")
