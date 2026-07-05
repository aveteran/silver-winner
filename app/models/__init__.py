"""
SQLAlchemy ORM 模型
所有数据库表模型集中导出
"""
from app.models.base import Base
from app.models.user import User
from app.models.position import PositionCategory, Position, PositionKeyword, ScoringWeight
from app.models.resume import Resume
from app.models.scoring import ScoringResult
from app.models.defect import DefectRule, ResumeDefect, OptimizationSuggestion
from app.models.history import HistoryRecord

__all__ = [
    "Base",
    "User",
    "PositionCategory",
    "Position",
    "PositionKeyword",
    "ScoringWeight",
    "Resume",
    "ScoringResult",
    "DefectRule",
    "ResumeDefect",
    "OptimizationSuggestion",
    "HistoryRecord",
]