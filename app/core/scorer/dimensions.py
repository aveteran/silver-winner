"""评分维度定义与计算方法"""
import re
from typing import Dict, Tuple
from app.core.extractor.section_splitter import ResumeSections
from app.models.position import Position
from app.utils.text_utils import count_chinese_chars, count_quantified_sentences


# 学历层次数值映射
EDUCATION_LEVEL = {
    "博士": 5, "硕士": 4, "研究生": 4, "Master": 4, "PhD": 5,
    "本科": 3, "学士": 3, "Bachelor": 3,
    "专科": 2, "大专": 2,
    "高中": 1, "中专": 1,
}

# 常见的量化动作动词
STRONG_VERBS = [
    "主导", "推动", "设计", "开发", "优化", "建立", "提升", "突破",
    "达成", "重构", "改进", "统筹", "实现", "完成", "解决", "突破",
    "创建", "打造", "引入", "增长", "降低", "节约",
]

# 弱动词
WEAK_VERBS = ["负责", "参与", "协助", "帮忙"]


def score_completeness(sections: ResumeSections) -> float:
    """
    内容完整度评分 (0-100)
    检查必填字段：姓名、联系方式(手机或邮箱)、教育、技能、经历
    """
    score = 0.0
    total_fields = 5

    if sections.name:
        score += 20
    if sections.phone or sections.email:
        score += 20
    if sections.education:
        score += 20
    if sections.skills and len(sections.skills) >= 2:
        score += 20
    if sections.work_experience or sections.projects:
        score += 20

    return score


def score_experience_match(
    sections: ResumeSections,
    keyword_result: Dict,
    position: Position,
) -> float:
    """
    经历匹配度评分 (0-100)
    基于关键词命中率 + 经历描述质量
    """
    # 关键词命中率（60分）
    hit_rate = keyword_result.get("hit_rate", 0)
    kw_score = hit_rate * 60

    # 经历描述丰富度（40分）
    exp_score = 0.0
    total_exp_items = len(sections.work_experience) + len(sections.projects)
    if total_exp_items >= 3:
        exp_score = 40
    elif total_exp_items == 2:
        exp_score = 30
    elif total_exp_items == 1:
        exp_score = 20
    else:
        exp_score = 0

    # 经历描述质量：检查是否包含量化数据
    has_quantified = False
    for exp in sections.work_experience:
        desc = exp.get("description", "")
        if re.search(r'\d+', desc) and len(desc) > 50:
            has_quantified = True
            break
    if not has_quantified:
        for proj in sections.projects:
            desc = proj.get("description", "")
            if re.search(r'\d+', desc) and len(desc) > 50:
                has_quantified = True
                break

    if has_quantified:
        exp_score = min(40, exp_score + 10)

    return kw_score + exp_score


def score_skill_coverage(
    sections: ResumeSections,
    keyword_result: Dict,
    position: Position,
) -> float:
    """
    技能覆盖度评分 (0-100)
    基于必备技能命中率 + 技能丰富度
    """
    # 必备技能命中率（70分）
    required_rate = keyword_result.get("required_hit_rate", 0)
    required_score = required_rate * 70

    # 技能总数丰富度（30分）
    skill_count = len(sections.skills)
    if skill_count >= 10:
        richness = 30
    elif skill_count >= 7:
        richness = 25
    elif skill_count >= 5:
        richness = 20
    elif skill_count >= 3:
        richness = 15
    else:
        richness = max(0, skill_count * 5)

    return required_score + richness


def score_education_match(
    sections: ResumeSections,
    position: Position,
) -> float:
    """
    教育匹配度评分 (0-100)
    基于学历层次匹配 + 专业相关性
    """
    score = 50.0  # 基准分

    if not sections.education:
        return 0

    # 获取最高学历
    max_edu_level = 0
    for edu in sections.education:
        degree = edu.get("degree", "")
        level = EDUCATION_LEVEL.get(degree, 0)
        if level > max_edu_level:
            max_edu_level = level

    # 学历层次评分（30分加成）
    if max_edu_level >= 5:
        score += 30
    elif max_edu_level >= 4:
        score += 25
    elif max_edu_level >= 3:
        score += 20
    elif max_edu_level >= 2:
        score += 10

    # 与岗位要求对比（20分调整）
    required_edu = position.education_required if position else ""
    if required_edu:
        required_level = EDUCATION_LEVEL.get(required_edu, 3)
        if max_edu_level >= required_level:
            score += 20
        elif max_edu_level >= required_level - 1:
            score += 5

    return min(100.0, score)


def score_expression_quality(sections: ResumeSections) -> float:
    """
    表达质量评分 (0-100)
    基于量化描述占比 + 强动词使用
    """
    score = 50.0

    # 检查量化描述
    quantified_count = count_quantified_sentences(sections.raw_text)
    if quantified_count >= 5:
        score += 25
    elif quantified_count >= 3:
        score += 20
    elif quantified_count >= 1:
        score += 10

    # 检查强动词使用 vs 弱动词
    text = sections.raw_text
    strong_count = sum(text.count(v) for v in STRONG_VERBS)
    weak_count = sum(text.count(v) for v in WEAK_VERBS)

    if strong_count >= 5:
        score += 15
    elif strong_count >= 3:
        score += 10
    elif strong_count >= 1:
        score += 5

    # 弱动词过多扣分
    if weak_count >= 5:
        score -= 10
    elif weak_count >= 3:
        score -= 5

    # 自我评价存在且有内容
    if sections.self_intro and len(sections.self_intro) > 30:
        score += 10

    return min(100.0, max(0, score))


def score_format_quality(sections: ResumeSections) -> float:
    """
    格式规范性评分 (0-100)
    基于篇幅、标点、排版
    """
    score = 70.0
    text = sections.raw_text

    # 篇幅检查
    char_count = len(text)
    if 500 <= char_count <= 1500:
        score += 15
    elif 200 <= char_count < 500:
        score += 5
    elif char_count < 200:
        score -= 20

    # 检查联系方式完整性
    if sections.phone and sections.email:
        score += 10
    elif sections.phone or sections.email:
        score += 5
    else:
        score -= 15

    # 检查是否有段落标题
    if any(kw in text for kw in ["教育", "经历", "技能", "项目"]):
        score += 5

    return min(100.0, max(0, score))


# 六维度评分函数注册表
DIMENSION_SCORERS = {
    "completeness": score_completeness,
    "experience": score_experience_match,
    "skill": score_skill_coverage,
    "education": score_education_match,
    "expression": score_expression_quality,
    "format": score_format_quality,
}

DIMENSION_NAMES = {
    "completeness": "内容完整度",
    "experience": "经历匹配度",
    "skill": "技能覆盖度",
    "education": "教育匹配度",
    "expression": "表达质量",
    "format": "格式规范性",
}
