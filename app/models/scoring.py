"""评分结果模型"""
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class ScoringResult(Base):
    __tablename__ = "scoring_results"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(
        ForeignKey("resumes.id"), unique=True, nullable=False, index=True
    )
    total_score: Mapped[float] = mapped_column(Float, nullable=False)
    completeness_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    experience_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    skill_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    education_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    expression_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    format_score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    grade: Mapped[str] = mapped_column(String(10), nullable=False)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    resume: Mapped["Resume"] = relationship(back_populates="scoring_result")

    def __repr__(self) -> str:
        return f"<ScoringResult(total={self.total_score}, grade='{self.grade}')>"
