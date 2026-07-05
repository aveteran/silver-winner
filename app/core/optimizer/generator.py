"""优化建议生成器：模板驱动 + 上下文填充"""
from __future__ import annotations
import logging
from typing import Dict, List
from dataclasses import dataclass, field
from app.core.defect.rules import DefectResult
from app.core.extractor.section_splitter import ResumeSections
from app.models.position import Position

logger = logging.getLogger(__name__)


@dataclass
class OptimizationItem:
    """单条优化建议"""
    category: str
    title: str
    content: str
    original_text: str = ""
    improved_example: str = ""


@dataclass
class OptimizationReport:
    """优化建议报告"""
    items: List[OptimizationItem] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.items)


# ==================== 优化模板库 ====================

OPTIMIZATION_TEMPLATES = {
    "MISSING_CONTACT": {
        "title": "补充完整联系方式",
        "content": (
            "简历缺少联系方式（手机号或邮箱），招聘方无法联系您。\n\n"
            "请在简历头部清晰标注：\n"
            "📞 手机：138-xxxx-xxxx\n"
            "📧 邮箱：yourname@example.com\n\n"
            "建议同时附上所在城市等信息。"
        ),
        "example": "📞 138-1234-5678 | 📧 zhang.san@email.com | 📍 北京市朝阳区",
    },
    "MISSING_EDUCATION": {
        "title": "完善教育经历信息",
        "content": (
            "教育背景是招聘方评估候选人的基础维度之一。当前简历中教育经历不完整。\n\n"
            "建议按以下格式补充：\n"
            "【学校名称】 | 【专业名称】 | 【学历：本科/硕士】 | 【起止年份】\n\n"
            "可额外添加：GPA（如3.5/4.0以上）、核心课程、学术荣誉等。"
        ),
        "example": "北京大学 | 计算机科学与技术 | 本科 | 2020.09 - 2024.06 | GPA 3.6/4.0",
    },
    "MISSING_SELF_INTRO": {
        "title": "添加自我介绍/个人评价",
        "content": (
            "一段好的自我介绍能让HR快速了解您的核心优势和职业规划。\n\n"
            "建议在简历开头添加2-3句自我总结：\n"
            "• 第1句：行业经验概括（如有经验）\n"
            "• 第2句：核心技能和擅长领域\n"
            "• 第3句：职业发展目标或求职方向"
        ),
        "example": (
            "3年互联网产品经理经验，擅长用户需求分析和产品策略规划。\n"
            "主导过DAU百万级产品的0-1搭建，具备优秀的数据驱动决策能力和跨团队协作能力。\n"
            "期望在快速成长的科技公司继续深耕产品方向。"
        ),
    },
    "WEAK_QUANTIFICATION": {
        "title": "强化经历中的量化成果",
        "content": (
            "您的经历描述中缺少具体的数据成果。仅使用「负责」「参与」等动词会显得空洞。\n\n"
            "建议使用STAR法则改写每段经历：\n"
            "• S (Situation)：项目背景\n"
            "• T (Task)：目标任务\n"
            "• A (Action)：具体行动\n"
            "• R (Result)：量化成果\n\n"
            "常见量化维度：增长百分比、绝对数值、效率提升、成本降低、团队规模等。"
        ),
        "example": (
            "❌ 原版：「负责公司公众号运营，提升粉丝量和阅读量」\n\n"
            "✅ 优化版：「主导公司公众号内容运营（S），通过选题优化和数据分析（A），"
            "6个月内粉丝增长150%（3万→7.5万），"
            "平均阅读量提升200%，产出10w+爆款文章3篇（R）」"
        ),
    },
    "SHORT_DESCRIPTION": {
        "title": "扩充项目/经历描述",
        "content": (
            "部分经历描述过于简短（少于50字），建议展开描述具体工作内容、使用的工具和取得成果。\n\n"
            "每段经历建议包含：\n"
            "• 项目/任务背景（1句）\n"
            "• 您的角色和具体行动（2-3句）\n"
            "• 使用的技术或工具\n"
            "• 取得的可量化成果"
        ),
        "example": (
            "❌ 原版：「参与XX系统开发」\n\n"
            "✅ 优化版：「参与XX订单管理系统后端开发，使用Spring Boot + MySQL技术栈，"
            "独立负责订单模块的设计与实现，系统上线后支撑日均10万笔订单处理，"
            "接口响应时间从2秒优化至200ms以内」"
        ),
    },
    "VERB_REPETITION": {
        "title": "替换单调动词，丰富表达",
        "content": (
            "简历中多次重复使用「负责」「参与」等动词，建议替换为更有力的动作动词。\n\n"
            "推荐替换词：\n"
            "• 负责 → 主导、统筹、推动\n"
            "• 参与 → 协作、配合、共建\n"
            "• 完成 → 达成、交付、交付上线\n"
            "• 做了 → 设计、开发、构建、打造\n"
            "• 帮助 → 支撑、赋能、推动"
        ),
        "example": (
            "❌ 原版：负责XX项目开发 / 参与YY功能迭代 / 协助团队完成ZZ\n"
            "✅ 优化版：主导XX项目从0到1开发 / 推动YY功能迭代落地 / 赋能团队达成ZZ目标"
        ),
    },
    "MISSING_CORE_KEYWORD": {
        "title": "补充岗位核心关键词",
        "content": (
            "目标岗位的核心必备技能未在您的简历中出现。在ATS（简历筛选系统）中，"
            "缺少关键词可能导致您的简历直接被筛除。\n\n"
            "操作建议：\n"
            "1. 如果您确实具备该技能：在技能列表和经历描述中明确写出\n"
            "2. 如果您正在学习该技能：可在简历中标注「了解XXX」「学习中XXX」\n"
            "3. 如果有替代技能：确保替代关键词出现在简历中"
        ),
        "example": (
            "如果岗位要求「Docker」但您简历中没有：\n"
            "• 技能列表中添加：Docker（熟悉容器化部署）\n"
            "• 经历中描述：「使用Docker容器化部署应用，实现一键发布和环境一致性」"
        ),
    },
    "TOO_SHORT": {
        "title": "大幅扩充简历内容",
        "content": (
            "简历总字数过少（<200字），信息量不足。一份完整的简历通常需要500-800字。\n\n"
            "建议补充以下内容板块：\n"
            "1. 完善教育背景（学校/专业/学历/毕业年份）\n"
            "2. 添加工作或实习经历（每段至少3-5行）\n"
            "3. 列出专业技能清单\n"
            "4. 添加2-3句自我评价\n"
            "5. 补充荣誉/证书信息\n"
            "6. 添加1-2个代表性项目经历"
        ),
        "example": "",
    },
    "TOO_LONG": {
        "title": "精简简历篇幅",
        "content": (
            "简历总字数超过2000字，建议精简至1-2页。HR平均浏览一份简历仅6-10秒。\n\n"
            "精简原则：\n"
            "• 删除与目标岗位无关的经历（如不相关的兼职）\n"
            "• 合并相似的工作内容描述\n"
            "• 5年以上的早期经历可以简写或删除\n"
            "• 删除过于详细的个人爱好\n"
            "• 保留最有代表性的2-3个项目"
        ),
        "example": "",
    },
    "EMPTY_SKILLS": {
        "title": "丰富技能列表",
        "content": (
            "技能列表过于简短（少于3项），无法体现您的专业能力。\n\n"
            "建议按类别补充：\n"
            "• 专业技能：编程语言、框架、专业知识\n"
            "• 工具/软件：开发工具、办公软件、设计工具\n"
            "• 语言能力：英语（CET-4/6、雅思、托福）、其他语言\n"
            "• 证书/资质：职业资格证、行业认证"
        ),
        "example": (
            "专业技能：Python, Java, SQL, 数据分析\n"
            "开发工具：Git, Docker, VS Code, Jupyter Notebook\n"
            "语言能力：英语 CET-6 (580), 普通话二级甲等\n"
            "证书：计算机二级、PMP项目管理认证"
        ),
    },
    "NO_HONORS": {
        "title": "补充荣誉/奖项/证书",
        "content": (
            "简历中未提及任何荣誉、奖项或证书。适当的荣誉展示可以增加简历的说服力。\n\n"
            "可以补充的类别：\n"
            "• 学业荣誉：奖学金、优秀毕业生、竞赛获奖\n"
            "• 工作荣誉：优秀员工、年度之星、项目奖\n"
            "• 专业证书：职业资格证、行业认证、语言证书\n"
            "• 其他：志愿者证书、培训认证"
        ),
        "example": (
            "🏆 2023年 国家励志奖学金\n"
            "🏆 2022年 全国大学生数学建模竞赛 省级一等奖\n"
            "📜 英语 CET-6 580分 | 📜 PMP项目管理认证"
        ),
    },
    "FORMAT_GENERAL": {
        "title": "优化简历格式与排版",
        "content": (
            "简历的格式规范性影响HR的第一印象。建议检查并优化以下方面：\n"
            "• 统一日期格式（建议：YYYY.MM 或 YYYY年M月）\n"
            "• 统一标点符号（中文简历使用中文标点）\n"
            "• 对齐缩进和段落间距\n"
            "• 使用清晰的分段标题区分各板块\n"
            "• 重要信息加粗突出"
        ),
        "example": "",
    },
}


def generate_optimizations(
    defects: List[DefectResult],
    sections: ResumeSections,
    position: Position | None = None,
) -> OptimizationReport:
    """
    根据缺陷检测结果生成优化建议

    Args:
        defects: 缺陷检测结果列表
        sections: 结构化简历信息
        position: 目标岗位

    Returns:
        OptimizationReport: 优化建议报告
    """
    report = OptimizationReport()
    seen_categories = set()

    for defect in defects:
        # 查找匹配的模板
        template = OPTIMIZATION_TEMPLATES.get(defect.rule_id)

        if template:
            # 合并同类缺陷（同类一个合并建议）
            if defect.category in seen_categories and defect.severity == "LOW":
                continue
            seen_categories.add(defect.category)

            # 提取原始文本片段（如果有）
            original = ""
            if defect.location and "教育" in defect.location:
                original = "\n".join(
                    edu.get("school", "") for edu in sections.education[:2]
                )
            elif defect.location and "工作" in defect.location:
                for exp in sections.work_experience[:1]:
                    original = exp.get("description", "")[:200]
            elif defect.location and "技能" in defect.location:
                original = "、".join(sections.skills[:5])

            item = OptimizationItem(
                category=defect.category,
                title=template["title"],
                content=template["content"],
                original_text=original,
                improved_example=template.get("example", ""),
            )
            report.items.append(item)
        else:
            # 无匹配模板时使用缺陷自带的建议
            item = OptimizationItem(
                category=defect.category,
                title=defect.name,
                content=defect.suggestion or f"建议修复：{defect.description}",
            )
            report.items.append(item)

    # 按优先级排序：信息缺失 > 描述薄弱 > 关键词 > 格式 > 篇幅
    category_order = {
        "信息缺失": 0, "描述薄弱": 1, "关键词缺失": 2,
        "逻辑问题": 3, "格式问题": 4, "篇幅问题": 5,
    }
    report.items.sort(key=lambda x: category_order.get(x.category, 99))

    logger.info(f"优化建议生成完成: {report.total}条")
    return report
