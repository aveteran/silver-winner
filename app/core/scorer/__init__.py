"""评分引擎模块"""
from app.core.scorer.engine import calculate_score, ScoringReport
from app.core.scorer.dimensions import DIMENSION_NAMES
from app.core.scorer.weight_manager import get_scoring_weights, get_score_grade, GRADE_DESCRIPTIONS
