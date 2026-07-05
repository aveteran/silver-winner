"""缺陷规则加载与评估"""
import json
import re
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from app.core.extractor.section_splitter import ResumeSections
from app.models.defect import DefectRule
from app.models.position import Position


@dataclass
class DefectResult:
    """单个缺陷检测结果"""
    rule_id: str
    category: str
    name: str
    severity: str
    description: str
    suggestion: str = ""
    location: str = ""


@dataclass
class DefectReport:
    """缺陷检测报告"""
    defects: List[DefectResult] = field(default_factory=list)
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0

    @property
    def total(self) -> int:
        return len(self.defects)


def run_defect_rules(
    sections: ResumeSections,
    rules: List[DefectRule],
    position: Optional[Position] = None,
    keyword_result: Optional[Dict] = None,
) -> DefectReport:
    """
    对简历执行缺陷规则检测

    Args:
        sections: 结构化简历信息
        rules: 缺陷规则列表（从数据库加载）
        position: 目标岗位（用于岗位相关规则）
        keyword_result: 关键词匹配结果（用于关键词缺失规则）

    Returns:
        DefectReport: 缺陷检测报告
    """
    report = DefectReport()

    for rule in rules:
        if not rule.is_active:
            continue

        try:
            result = _evaluate_rule(rule, sections, position, keyword_result)
            if result:
                report.defects.append(result)
        except Exception:
            continue  # 单条规则失败不影响整体

    # 统计
    for d in report.defects:
        if d.severity == "HIGH":
            report.high_count += 1
        elif d.severity == "MEDIUM":
            report.medium_count += 1
        else:
            report.low_count += 1

    # 排序：严重度高的在前
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    report.defects.sort(key=lambda d: severity_order.get(d.severity, 99))

    return report


def _evaluate_rule(
    rule: DefectRule,
    sections: ResumeSections,
    position: Optional[Position],
    keyword_result: Optional[Dict],
) -> Optional[DefectResult]:
    """评估单条缺陷规则"""

    # 解析条件
    condition = {}
    if rule.condition_json:
        try:
            condition = json.loads(rule.condition_json)
        except json.JSONDecodeError:
            condition = {}

    triggered = False
    location = ""

    # ---- 信息缺失类规则 ----
    if rule.rule_id == "MISSING_CONTACT":
        if not sections.phone and not sections.email:
            triggered = True
            location = "简历头部"

    elif rule.rule_id == "MISSING_EDUCATION":
        if not sections.education:
            triggered = True
            location = "教育经历段落"

    elif rule.rule_id == "MISSING_SELF_INTRO":
        if not sections.self_intro or len(sections.self_intro) < 20:
            triggered = True
            location = "自我介绍段落"

    elif rule.rule_id == "MISSING_EXPECTATION":
        if not sections.expected_position:
            triggered = True
            location = "简历头部"

    elif rule.rule_id == "EMPTY_SKILLS":
        min_skills = condition.get("min_skills", 3)
        if len(sections.skills) < min_skills:
            triggered = True
            location = "技能列表"

    # ---- 描述薄弱类规则 ----
    elif rule.rule_id == "WEAK_QUANTIFICATION":
        text = sections.raw_text
        weak_patterns = condition.get("check_patterns", ["负责", "参与", "协助"])
        weak_count = sum(text.count(p) for p in weak_patterns)
        if weak_count >= 3:
            # 检查是否有足够的量化描述
            quantified_count = len(re.findall(r'\d+[%％个项人万次]', text))
            if quantified_count < weak_count:
                triggered = True
                location = "工作/项目经历段落"

    elif rule.rule_id == "SHORT_DESCRIPTION":
        min_chars = condition.get("min_chars_per_item", 50)
        for exp in sections.work_experience:
            desc = exp.get("description", "")
            if len(desc) < min_chars and len(desc) > 0:
                triggered = True
                location = "工作经历段落"
                break
        if not triggered:
            for proj in sections.projects:
                desc = proj.get("description", "")
                if len(desc) < min_chars and len(desc) > 0:
                    triggered = True
                    location = "项目经历段落"
                    break

    elif rule.rule_id == "VERB_REPETITION":
        text = sections.raw_text
        repetitive = condition.get("repetitive_verbs", ["负责", "参与", "协助"])
        min_rep = condition.get("min_repetition", 3)
        for verb in repetitive:
            if text.count(verb) >= min_rep:
                triggered = True
                location = "全文"
                break

    # ---- 格式问题类规则 ----
    elif rule.rule_id == "PUNCTUATION_MIX":
        import re as re_mod
        has_chinese = bool(re_mod.search(r'[，。；：「」『』！？、]', sections.raw_text))
        has_english = bool(re_mod.search(r'[,\.;:\'"!?]', sections.raw_text))
        if has_chinese and has_english:
            triggered = True
            location = "全文"

    elif rule.rule_id == "DATE_FORMAT_INCONSISTENT":
        # 检查是否存在多种日期格式
        formats = []
        if re.search(r'\d{4}\.\d{1,2}', sections.raw_text):
            formats.append("YYYY.MM")
        if re.search(r'\d{4}-\d{1,2}', sections.raw_text):
            formats.append("YYYY-MM")
        if re.search(r'\d{4}年\d{1,2}月', sections.raw_text):
            formats.append("YYYY年M月")
        if len(formats) > 1:
            triggered = True
            location = "教育/工作经历段落"

    # ---- 逻辑问题类规则 ----
    elif rule.rule_id == "TIME_OVERLAP":
        # 简化检查：有两个以上工作经历
        if len(sections.work_experience) >= 2:
            triggered = False
            # 此处可以更详细地检查时间重叠，简化处理
            location = "工作经历段落"

    # ---- 关键词缺失类规则 ----
    elif rule.rule_id == "MISSING_CORE_KEYWORD":
        if keyword_result and position:
            miss_required = keyword_result.get("miss_required", [])
            if miss_required:
                triggered = True
                # 填充模板
                kw_names = [kw["keyword"] for kw in miss_required[:3]]
                location = "技能列表/全文"
                # 动态生成描述
                rule.description_template = rule.description_template.replace(
                    "{position}", position.name
                ).replace("{keyword}", "、".join(kw_names))

    # ---- 篇幅问题类规则 ----
    elif rule.rule_id == "TOO_SHORT":
        min_chars = condition.get("min_total_chars", 200)
        if len(sections.raw_text) < min_chars:
            triggered = True
            location = "全文"

    elif rule.rule_id == "TOO_LONG":
        max_chars = condition.get("max_total_chars", 2000)
        if len(sections.raw_text) > max_chars:
            triggered = True
            location = "全文"

    # ---- 新增规则 ----
    elif rule.rule_id == "NO_HONORS":
        if not sections.honors and not sections.certificates:
            triggered = True
            location = "荣誉/证书段落"

    elif rule.rule_id == "EDUCATION_MISMATCH":
        if position and position.education_required and sections.education:
            # 检查学历是否满足要求
            edu_levels = {"博士": 5, "硕士": 4, "本科": 3, "专科": 2}
            required = edu_levels.get(position.education_required, 3)
            max_edu = 0
            for edu in sections.education:
                level = edu_levels.get(edu.get("degree", ""), 0)
                max_edu = max(max_edu, level)
            if max_edu < required:
                triggered = True
                location = "教育经历段落"
                rule.description_template = rule.description_template.replace(
                    "{position}", position.name
                ).replace("{required_education}", position.education_required)

    if triggered:
        # 填充描述和优化建议模板
        description = rule.description_template or f"检测到{rule.name}"
        suggestion = rule.suggestion_template or ""

        return DefectResult(
            rule_id=rule.rule_id,
            category=rule.category,
            name=rule.name,
            severity=rule.severity,
            description=description,
            suggestion=suggestion,
            location=location,
        )

    return None
