"""评分权重管理器：按岗位自动加载权重"""
from __future__ import annotations
from typing import Dict
from app.models.position import Position


# 默认评分权重（无岗位匹配时使用）
DEFAULT_WEIGHTS: Dict[str, float] = {
    "completeness": 0.20,
    "experience": 0.30,
    "skill": 0.20,
    "education": 0.15,
    "expression": 0.10,
    "format": 0.05,
}


def get_scoring_weights(position: Position | None) -> Dict[str, float]:
    """获取评分权重（优先岗位配置，fallback到默认）"""
    if position and position.scoring_weights:
        weights = {}
        for sw in position.scoring_weights:
            weights[sw.dimension] = sw.weight
        # 补齐缺失的维度
        for dim, default_w in DEFAULT_WEIGHTS.items():
            if dim not in weights:
                weights[dim] = default_w
        return weights

    return dict(DEFAULT_WEIGHTS)


def get_score_grade(total_score: float) -> str:
    """根据总分返回等级"""
    if total_score >= 90:
        return "S"
    elif total_score >= 80:
        return "A"
    elif total_score >= 65:
        return "B"
    elif total_score >= 50:
        return "C"
    else:
        return "D"


GRADE_DESCRIPTIONS = {
    "S": "卓越 — 简历非常优秀，与目标岗位高度匹配",
    "A": "优秀 — 简历质量较高，有少量可优化空间",
    "B": "良好 — 简历基本合格，建议针对性优化",
    "C": "一般 — 简历存在较多不足，需要显著改进",
    "D": "需改进 — 简历有严重缺陷，建议重新撰写",
}
