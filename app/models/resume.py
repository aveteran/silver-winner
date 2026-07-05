"""简历模型"""
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    target_position_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("positions.id"), nullable=True
    )
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    structured_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(
        String(20), default="pending", nullable=False
    )
    parse_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="resumes")
    target_position: Mapped[Optional["Position"]] = relationship()
    scoring_result: Mapped[Optional["ScoringResult"]] = relationship(
        back_populates="resume", uselist=False, cascade="all, delete-orphan"
    )
    defects: Mapped[List["ResumeDefect"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )
    optimization_suggestions: Mapped[List["OptimizationSuggestion"]] = relationship(
        back_populates="resume", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Resume(id={self.id}, file='{self.original_filename}', status='{self.parse_status}')>"
