"""缺陷检测与优化建议模型"""
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class DefectRule(Base):
    """缺陷规则库"""
    __tablename__ = "defect_rules"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    rule_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    condition_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="MEDIUM")
    description_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    suggestion_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<DefectRule(rule_id='{self.rule_id}', severity='{self.severity}')>"


class ResumeDefect(Base):
    """简历检测到的缺陷"""
    __tablename__ = "resume_defects"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"), nullable=False, index=True)
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    resume: Mapped["Resume"] = relationship(back_populates="defects")

    def __repr__(self) -> str:
        return f"<ResumeDefect(category='{self.category}', severity='{self.severity}')>"


class OptimizationSuggestion(Base):
    """优化建议"""
    __tablename__ = "optimization_suggestions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"), nullable=False, index=True)
    defect_id: Mapped[Optional[int]] = mapped_column(ForeignKey("resume_defects.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    original_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    improved_example: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    resume: Mapped["Resume"] = relationship(back_populates="optimization_suggestions")

    def __repr__(self) -> str:
        return f"<OptimizationSuggestion(title='{self.title}')>"
