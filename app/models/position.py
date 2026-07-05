"""岗位相关模型：岗位大类、岗位库、关键词、评分权重"""
from typing import List, Optional
from sqlalchemy import String, Integer, Float, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base


class PositionCategory(Base):
    """岗位大类（IT技术/商务管理/工程技术/教育医疗/综合通用）"""
    __tablename__ = "position_categories"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    positions: Mapped[List["Position"]] = relationship(back_populates="category", lazy="selectin")

    def __repr__(self) -> str:
        return f"<PositionCategory(name='{self.name}')>"


class Position(Base):
    """具体岗位"""
    __tablename__ = "positions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("position_categories.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    education_required: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    experience_years: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    category: Mapped["PositionCategory"] = relationship(back_populates="positions")
    keywords: Mapped[List["PositionKeyword"]] = relationship(back_populates="position", lazy="selectin", cascade="all, delete-orphan")
    scoring_weights: Mapped[List["ScoringWeight"]] = relationship(back_populates="position", lazy="selectin", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Position(name='{self.name}')>"


class PositionKeyword(Base):
    """岗位技能关键词"""
    __tablename__ = "position_keywords"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    position_id: Mapped[int] = mapped_column(ForeignKey("positions.id"), nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(80), nullable=False)
    keyword_type: Mapped[str] = mapped_column(
        String(20), default="skill", nullable=False
    )  # skill / tool / certification / soft_skill
    weight: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    position: Mapped["Position"] = relationship(back_populates="keywords")

    def __repr__(self) -> str:
        return f"<PositionKeyword(keyword='{self.keyword}', type='{self.keyword_type}')>"


class ScoringWeight(Base):
    """评分维度权重配置（按岗位）"""
    __tablename__ = "scoring_weights"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    position_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("positions.id"), nullable=True, index=True
    )
    dimension: Mapped[str] = mapped_column(String(30), nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)
    threshold: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)

    position: Mapped[Optional["Position"]] = relationship(back_populates="scoring_weights")

    def __repr__(self) -> str:
        return f"<ScoringWeight(dim='{self.dimension}', w={self.weight})>"
