"""评分主引擎：汇聚六维度评分 + 权重计算 = 总分"""
from __future__ import annotations
from typing import Dict
from dataclasses import dataclass, field
from app.core.extractor.section_splitter import ResumeSections
from app.core.scorer.dimensions import DIMENSION_SCORERS, DIMENSION_NAMES
from app.core.scorer.weight_manager import get_scoring_weights, get_score_grade, GRADE_DESCRIPTIONS
from app.models.position import Position


@dataclass
class ScoringReport:
    """评分报告"""
    total_score: float = 0.0
    grade: str = "D"
    grade_description: str = ""
    dimension_scores: Dict[str, float] = field(default_factory=dict)
    dimension_labels: Dict[str, str] = field(default_factory=dict)
    weights_used: Dict[str, float] = field(default_factory=dict)
    position_name: str = ""


def calculate_score(
    sections: ResumeSections,
    position: Position | None,
    keyword_result: Dict,
) -> ScoringReport:
    """
    计算简历综合得分

    Args:
        sections: 结构化简历信息
        position: 目标岗位（可为None）
        keyword_result: 关键词匹配结果

    Returns:
        ScoringReport: 完整评分报告
    """
    # 1. 获取权重配置
    weights = get_scoring_weights(position)

    # 2. 计算各维度原始得分
    position_name = position.name if position else "通用评估"

    raw_scores = {}
    for dim_key, scorer_fn in DIMENSION_SCORERS.items():
        try:
            if dim_key in ("experience", "skill"):
                # 需要keyword_result和position参数的维度
                if dim_key == "experience":
                    raw_scores[dim_key] = scorer_fn(sections, keyword_result, position)
                else:
                    raw_scores[dim_key] = scorer_fn(sections, keyword_result, position)
            elif dim_key == "education":
                raw_scores[dim_key] = scorer_fn(sections, position)
            else:
                raw_scores[dim_key] = scorer_fn(sections)
        except Exception as e:
            # 评分失败时给默认分
            raw_scores[dim_key] = 50.0

    # 3. 加权计算总分
    total = 0.0
    for dim_key, score in raw_scores.items():
        weight = weights.get(dim_key, 0.15)
        total += score * weight

    # 4. 确定等级
    grade = get_score_grade(total)
    grade_desc = GRADE_DESCRIPTIONS.get(grade, "")

    # 5. 构建报告
    report = ScoringReport(
        total_score=round(total, 1),
        grade=grade,
        grade_description=grade_desc,
        dimension_scores={k: round(v, 1) for k, v in raw_scores.items()},
        dimension_labels=DIMENSION_NAMES,
        weights_used=weights,
        position_name=position_name,
    )

    return report
