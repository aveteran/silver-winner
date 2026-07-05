"""
数据库初始化与种子数据
首次运行时创建所有表并导入预置数据（岗位、关键词、评分权重、缺陷规则）
"""
import json
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.config import settings
from app.models.base import Base
from app.models import (
    User, PositionCategory, Position, PositionKeyword,
    ScoringWeight, DefectRule
)
from app.core.security import hash_password

logger = logging.getLogger(__name__)

# 六维度名称常量
DIMENSIONS = ["completeness", "experience", "skill", "education", "expression", "format"]
DIMENSION_LABELS = {
    "completeness": "内容完整度",
    "experience": "经历匹配度",
    "skill": "技能覆盖度",
    "education": "教育匹配度",
    "expression": "表达质量",
    "format": "格式规范性",
}

# ==================== 种子数据定义 ====================

# 岗位大类
CATEGORIES = [
    {"name": "IT技术类", "description": "计算机/互联网/软件相关岗位", "sort_order": 1},
    {"name": "商务管理类", "description": "市场营销/人力资源/财务/管理相关岗位", "sort_order": 2},
    {"name": "工程技术类", "description": "机械/电气/土木/建筑/化工相关岗位", "sort_order": 3},
    {"name": "教育医疗类", "description": "教师/培训/医疗/护理相关岗位", "sort_order": 4},
    {"name": "综合通用类", "description": "行政/客服/运营/编辑/物流等通用岗位", "sort_order": 5},
]

# 岗位定义：(大类索引, 岗位名, 学历要求, 经验年限)
POSITIONS_DATA = [
    # IT技术类
    (0, "Python开发工程师", "本科", 1),
    (0, "Java后端工程师", "本科", 1),
    (0, "前端开发工程师", "本科", 1),
    (0, "数据分析师", "本科", 1),
    (0, "算法工程师", "硕士", 2),
    (0, "软件测试工程师", "本科", 0),
    (0, "运维工程师", "专科", 1),
    (0, "产品经理", "本科", 2),
    (0, "UI设计师", "专科", 1),
    (0, "网络安全工程师", "本科", 1),
    # 商务管理类
    (1, "市场营销专员", "专科", 0),
    (1, "人力资源专员", "本科", 0),
    (1, "财务会计", "本科", 1),
    (1, "项目经理", "本科", 3),
    (1, "销售代表", "专科", 0),
    (1, "品牌策划", "本科", 1),
    (1, "行政管理", "专科", 0),
    (1, "供应链管理", "本科", 1),
    # 工程技术类
    (2, "机械工程师", "本科", 1),
    (2, "电气工程师", "本科", 1),
    (2, "土木工程师", "本科", 1),
    (2, "建筑设计师", "本科", 2),
    (2, "环境工程师", "本科", 1),
    (2, "化工工程师", "本科", 1),
    (2, "质量工程师", "本科", 2),
    # 教育医疗类
    (3, "中小学教师", "本科", 0),
    (3, "大学讲师", "硕士", 1),
    (3, "企业培训师", "本科", 2),
    (3, "临床医生", "硕士", 2),
    (3, "护理人员", "专科", 0),
    (3, "药剂师", "本科", 1),
    (3, "医学检验师", "本科", 1),
    # 综合通用类
    (4, "行政文员", "专科", 0),
    (4, "客服专员", "高中", 0),
    (4, "新媒体运营", "专科", 1),
    (4, "内容编辑", "本科", 1),
    (4, "英语翻译", "本科", 1),
    (4, "法律顾问", "本科", 2),
    (4, "物业管理", "专科", 1),
    (4, "物流专员", "专科", 0),
]

# 岗位关键词：(岗位名, 关键词, 类型, 权重, 是否必备)
# 类型: skill=专业技能, tool=工具, certification=证书, soft_skill=软技能
POSITION_KEYWORDS_DATA = {
    "Python开发工程师": [
        ("Python", "skill", 1.0, True), ("Django", "skill", 0.8, False),
        ("Flask", "skill", 0.8, False), ("FastAPI", "skill", 0.8, False),
        ("MySQL", "tool", 0.7, False), ("Redis", "tool", 0.6, False),
        ("Docker", "tool", 0.6, False), ("Git", "tool", 0.6, False),
        ("Linux", "skill", 0.7, False), ("RESTful API", "skill", 0.7, False),
        ("数据结构", "skill", 0.8, True), ("算法", "skill", 0.8, True),
        ("面向对象编程", "skill", 0.6, False), ("单元测试", "skill", 0.5, False),
        ("团队协作", "soft_skill", 0.5, False), ("问题解决", "soft_skill", 0.5, False),
    ],
    "Java后端工程师": [
        ("Java", "skill", 1.0, True), ("Spring Boot", "skill", 0.9, True),
        ("Spring Cloud", "skill", 0.7, False), ("MyBatis", "skill", 0.7, False),
        ("MySQL", "tool", 0.8, True), ("Redis", "tool", 0.6, False),
        ("微服务", "skill", 0.7, False), ("Docker", "tool", 0.6, False),
        ("JVM", "skill", 0.7, False), ("多线程", "skill", 0.7, False),
    ],
    "前端开发工程师": [
        ("HTML", "skill", 0.9, True), ("CSS", "skill", 0.9, True),
        ("JavaScript", "skill", 1.0, True), ("Vue.js", "skill", 0.8, False),
        ("React", "skill", 0.8, False), ("TypeScript", "skill", 0.7, False),
        ("Node.js", "skill", 0.5, False), ("Webpack", "tool", 0.5, False),
        ("响应式设计", "skill", 0.6, False), ("Git", "tool", 0.5, False),
    ],
    "数据分析师": [
        ("Python", "skill", 0.9, True), ("SQL", "skill", 0.9, True),
        ("数据分析", "skill", 0.8, True), ("Excel", "tool", 0.6, False),
        ("Tableau", "tool", 0.5, False), ("Pandas", "skill", 0.7, False),
        ("NumPy", "skill", 0.6, False), ("数据可视化", "skill", 0.7, False),
        ("统计学", "skill", 0.8, True), ("机器学习", "skill", 0.5, False),
    ],
    "算法工程师": [
        ("Python", "skill", 0.9, True), ("机器学习", "skill", 1.0, True),
        ("深度学习", "skill", 0.9, True), ("PyTorch", "tool", 0.8, False),
        ("TensorFlow", "tool", 0.7, False), ("数据结构", "skill", 0.8, True),
        ("算法", "skill", 1.0, True), ("数学", "skill", 0.8, True),
        ("NLP", "skill", 0.6, False), ("计算机视觉", "skill", 0.6, False),
    ],
    "软件测试工程师": [
        ("测试用例", "skill", 0.9, True), ("自动化测试", "skill", 0.8, True),
        ("Selenium", "tool", 0.6, False), ("JMeter", "tool", 0.5, False),
        ("Python", "skill", 0.6, False), ("功能测试", "skill", 0.7, False),
        ("性能测试", "skill", 0.6, False), ("Bug跟踪", "skill", 0.6, False),
    ],
    "运维工程师": [
        ("Linux", "skill", 1.0, True), ("Docker", "tool", 0.8, True),
        ("Kubernetes", "tool", 0.7, False), ("Shell", "skill", 0.7, False),
        ("Jenkins", "tool", 0.6, False), ("监控", "skill", 0.6, False),
        ("网络", "skill", 0.7, False), ("自动化运维", "skill", 0.7, False),
    ],
    "产品经理": [
        ("需求分析", "skill", 0.9, True), ("产品设计", "skill", 0.8, True),
        ("Axure", "tool", 0.6, False), ("PRD", "skill", 0.7, False),
        ("用户调研", "skill", 0.7, False), ("敏捷开发", "skill", 0.6, False),
        ("竞品分析", "skill", 0.7, False), ("沟通协调", "soft_skill", 0.7, True),
    ],
    "UI设计师": [
        ("Figma", "tool", 0.8, True), ("Sketch", "tool", 0.6, False),
        ("Photoshop", "tool", 0.7, False), ("UI设计", "skill", 0.9, True),
        ("UX设计", "skill", 0.7, False), ("交互设计", "skill", 0.7, False),
        ("设计规范", "skill", 0.6, False), ("用户研究", "skill", 0.5, False),
    ],
    "网络安全工程师": [
        ("网络安全", "skill", 1.0, True), ("渗透测试", "skill", 0.7, False),
        ("防火墙", "skill", 0.6, False), ("安全审计", "skill", 0.6, False),
        ("Python", "skill", 0.6, False), ("Linux", "skill", 0.7, False),
        ("漏洞扫描", "skill", 0.7, False),
    ],
    "市场营销专员": [
        ("市场调研", "skill", 0.7, False), ("营销策划", "skill", 0.8, True),
        ("数据分析", "skill", 0.6, False), ("Excel", "tool", 0.6, False),
        ("新媒体运营", "skill", 0.6, False), ("沟通能力", "soft_skill", 0.8, True),
        ("文案写作", "skill", 0.6, False), ("活动策划", "skill", 0.6, False),
    ],
    "人力资源专员": [
        ("招聘", "skill", 0.8, True), ("员工培训", "skill", 0.6, False),
        ("绩效管理", "skill", 0.6, False), ("劳动法", "skill", 0.7, False),
        ("Office", "tool", 0.6, False), ("沟通协调", "soft_skill", 0.8, True),
    ],
    "财务会计": [
        ("会计", "skill", 1.0, True), ("财务报表", "skill", 0.8, True),
        ("用友", "tool", 0.5, False), ("金蝶", "tool", 0.5, False),
        ("Excel", "tool", 0.7, False), ("税务", "skill", 0.7, False),
        ("会计从业资格证", "certification", 0.6, False),
    ],
    "项目经理": [
        ("项目管理", "skill", 1.0, True), ("PMP", "certification", 0.6, False),
        ("团队管理", "skill", 0.8, True), ("风险管理", "skill", 0.6, False),
        ("沟通协调", "soft_skill", 0.8, True), ("敏捷", "skill", 0.6, False),
    ],
    "销售代表": [
        ("销售", "skill", 1.0, True), ("客户关系", "skill", 0.8, True),
        ("谈判", "skill", 0.7, False), ("沟通能力", "soft_skill", 0.9, True),
        ("CRM", "tool", 0.5, False),
    ],
    "品牌策划": [
        ("品牌策划", "skill", 0.9, True), ("文案写作", "skill", 0.7, False),
        ("市场营销", "skill", 0.7, False), ("创意设计", "skill", 0.6, False),
        ("数据分析", "skill", 0.5, False),
    ],
    "行政管理": [
        ("行政", "skill", 0.8, True), ("Office", "tool", 0.7, True),
        ("文档管理", "skill", 0.6, False), ("会议组织", "skill", 0.5, False),
        ("沟通协调", "soft_skill", 0.7, True),
    ],
    "供应链管理": [
        ("供应链", "skill", 0.9, True), ("物流管理", "skill", 0.7, False),
        ("ERP", "tool", 0.6, False), ("库存管理", "skill", 0.6, False),
        ("采购管理", "skill", 0.6, False),
    ],
    "机械工程师": [
        ("AutoCAD", "tool", 0.8, True), ("SolidWorks", "tool", 0.7, False),
        ("机械设计", "skill", 0.9, True), ("机械制图", "skill", 0.7, False),
        ("有限元分析", "skill", 0.5, False), ("材料力学", "skill", 0.6, False),
    ],
    "电气工程师": [
        ("电气设计", "skill", 0.9, True), ("PLC", "skill", 0.7, False),
        ("AutoCAD", "tool", 0.7, False), ("供配电", "skill", 0.6, False),
        ("继电保护", "skill", 0.5, False), ("电气自动化", "skill", 0.6, False),
    ],
    "土木工程师": [
        ("AutoCAD", "tool", 0.7, False), ("土木工程", "skill", 0.9, True),
        ("结构设计", "skill", 0.7, False), ("施工管理", "skill", 0.6, False),
        ("工程测量", "skill", 0.6, False), ("PKPM", "tool", 0.5, False),
    ],
    "建筑设计师": [
        ("建筑设计", "skill", 0.9, True), ("AutoCAD", "tool", 0.7, True),
        ("SketchUp", "tool", 0.6, False), ("BIM", "skill", 0.6, False),
        ("3D Max", "tool", 0.5, False), ("建筑规范", "skill", 0.6, False),
    ],
    "中小学教师": [
        ("教学", "skill", 0.9, True), ("教师资格证", "certification", 0.8, True),
        ("班级管理", "skill", 0.6, False), ("课程设计", "skill", 0.6, False),
        ("普通话", "skill", 0.5, False), ("沟通能力", "soft_skill", 0.8, True),
    ],
    "临床医生": [
        ("临床医学", "skill", 1.0, True), ("执业医师资格证", "certification", 0.9, True),
        ("病历书写", "skill", 0.6, False), ("医学影像", "skill", 0.5, False),
        ("沟通能力", "soft_skill", 0.6, False),
    ],
    "护理人员": [
        ("护理", "skill", 1.0, True), ("护士执业证", "certification", 0.9, True),
        ("无菌操作", "skill", 0.6, False), ("病情观察", "skill", 0.6, False),
        ("沟通能力", "soft_skill", 0.6, False),
    ],
    "新媒体运营": [
        ("新媒体运营", "skill", 0.9, True), ("文案写作", "skill", 0.7, False),
        ("短视频", "skill", 0.6, False), ("数据分析", "skill", 0.5, False),
        ("微信公众号", "tool", 0.6, False), ("抖音", "tool", 0.5, False),
    ],
    "内容编辑": [
        ("编辑", "skill", 0.9, True), ("文案写作", "skill", 0.8, True),
        ("校对", "skill", 0.6, False), ("排版", "skill", 0.5, False),
        ("Office", "tool", 0.5, False),
    ],
    "英语翻译": [
        ("英语", "skill", 1.0, True), ("TEM-8", "certification", 0.6, False),
        ("翻译", "skill", 0.9, True), ("CAT", "tool", 0.5, False),
        ("笔译", "skill", 0.7, False), ("口译", "skill", 0.7, False),
    ],
    "行政文员": [
        ("Office", "tool", 0.7, True), ("文档管理", "skill", 0.6, False),
        ("行政", "skill", 0.7, True), ("沟通协调", "soft_skill", 0.6, True),
    ],
    "环境工程师": [
        ("环境工程", "skill", 0.9, True), ("水处理", "skill", 0.6, False),
        ("环评", "skill", 0.6, False), ("CAD", "tool", 0.5, False),
        ("环境监测", "skill", 0.7, False),
    ],
    "化工工程师": [
        ("化工", "skill", 0.9, True), ("化工原理", "skill", 0.7, False),
        ("AutoCAD", "tool", 0.6, False), ("工艺设计", "skill", 0.6, False),
        ("安全生产", "skill", 0.5, False),
    ],
    "质量工程师": [
        ("质量管理", "skill", 0.9, True), ("ISO", "skill", 0.6, False),
        ("质量体系", "skill", 0.7, True), ("SPC", "tool", 0.5, False),
        ("六西格玛", "skill", 0.5, False),
    ],
    "大学讲师": [
        ("教学", "skill", 0.8, True), ("科研", "skill", 0.7, False),
        ("论文", "skill", 0.6, False), ("教师资格证", "certification", 0.7, True),
        ("专业领域", "skill", 0.9, True),
    ],
    "企业培训师": [
        ("培训", "skill", 0.9, True), ("课程开发", "skill", 0.7, False),
        ("PPT", "tool", 0.6, False), ("演讲", "skill", 0.7, False),
        ("沟通能力", "soft_skill", 0.8, True),
    ],
    "药剂师": [
        ("药学", "skill", 0.9, True), ("执业药师资格证", "certification", 0.9, True),
        ("药物知识", "skill", 0.8, True), ("处方审核", "skill", 0.7, False),
    ],
    "医学检验师": [
        ("医学检验", "skill", 0.9, True), ("检验仪器", "skill", 0.6, False),
        ("实验室", "skill", 0.6, False), ("质量控制", "skill", 0.5, False),
    ],
    "客服专员": [
        ("客服", "skill", 0.9, True), ("沟通能力", "soft_skill", 0.9, True),
        ("Office", "tool", 0.5, False), ("CRM系统", "tool", 0.5, False),
    ],
    "法律顾问": [
        ("法律", "skill", 1.0, True), ("法律职业资格证", "certification", 0.8, True),
        ("合同法", "skill", 0.7, False), ("公司法", "skill", 0.7, False),
        ("法律文书", "skill", 0.6, False),
    ],
    "物业管理": [
        ("物业管理", "skill", 0.8, True), ("物业法规", "skill", 0.6, False),
        ("客户服务", "skill", 0.6, False), ("设施管理", "skill", 0.5, False),
    ],
    "物流专员": [
        ("物流管理", "skill", 0.8, True), ("仓储管理", "skill", 0.6, False),
        ("ERP", "tool", 0.5, False), ("供应链", "skill", 0.5, False),
    ],
}

# 岗位类别默认权重（按大类维度配置）
CATEGORY_WEIGHTS = {
    "IT技术类": {"completeness": 0.20, "experience": 0.30, "skill": 0.25, "education": 0.10, "expression": 0.10, "format": 0.05},
    "商务管理类": {"completeness": 0.20, "experience": 0.30, "skill": 0.15, "education": 0.10, "expression": 0.20, "format": 0.05},
    "工程技术类": {"completeness": 0.20, "experience": 0.30, "skill": 0.20, "education": 0.15, "expression": 0.10, "format": 0.05},
    "教育医疗类": {"completeness": 0.25, "experience": 0.20, "skill": 0.20, "education": 0.20, "expression": 0.10, "format": 0.05},
    "综合通用类": {"completeness": 0.25, "experience": 0.25, "skill": 0.15, "education": 0.10, "expression": 0.20, "format": 0.05},
}

# 缺陷规则种子数据
DEFECT_RULES = [
    {
        "rule_id": "MISSING_CONTACT", "category": "信息缺失",
        "name": "缺少联系方式", "severity": "HIGH",
        "condition_json": '{"required_fields": ["phone", "email"], "min_count": 1}',
        "description_template": "简历中未找到联系方式（手机号或邮箱），招聘方无法联系您。请在简历头部清晰标注手机号和电子邮箱。",
        "suggestion_template": "建议在简历顶部添加：\n📞 手机：138-xxxx-xxxx\n📧 邮箱：yourname@example.com",
    },
    {
        "rule_id": "MISSING_EDUCATION", "category": "信息缺失",
        "name": "教育经历不完整", "severity": "HIGH",
        "condition_json": '{"required_sections": ["education"], "min_chars": 10}',
        "description_template": "简历中缺少教育经历或描述过于简略。教育背景是招聘方关注的基础信息。",
        "suggestion_template": "建议补充以下格式的教育经历：\n[学校名称] | [专业名称] | [学历:本科/硕士] | [起止年份]\n可额外添加：GPA、相关课程、荣誉奖项",
    },
    {
        "rule_id": "MISSING_SELF_INTRO", "category": "信息缺失",
        "name": "缺少自我介绍", "severity": "MEDIUM",
        "condition_json": '{"required_sections": ["self_intro", "个人评价", "自我介绍"], "min_chars": 30}',
        "description_template": "简历缺少自我介绍/个人评价段落。一段好的自我介绍能让HR快速了解您的优势。",
        "suggestion_template": "建议在简历开头添加2-3句自我介绍：\n「XX年XX行业工作经验，擅长XXX，曾主导XXX项目并取得XXX成果。具备良好的XXX能力和XXX能力。」",
    },
    {
        "rule_id": "MISSING_EXPECTATION", "category": "信息缺失",
        "name": "缺少求职意向", "severity": "MEDIUM",
        "condition_json": '{"required_fields": ["期望职位", "求职意向", "期望城市"]}',
        "description_template": "简历未包含明确的求职意向（期望职位、城市、薪资等），建议补充。",
        "suggestion_template": "建议在简历顶部添加求职意向栏：\n期望职位：XXX | 期望城市：XXX | 期望薪资：XXX | 到岗时间：XXX",
    },
    {
        "rule_id": "WEAK_QUANTIFICATION", "category": "描述薄弱",
        "name": "经历缺乏量化成果", "severity": "HIGH",
        "condition_json": '{"check_patterns": ["负责", "参与", "协助"], "no_number_ratio": 0.7}',
        "description_template": "您的{section}描述缺乏具体的量化成果。仅使用「负责」「参与」等动词会显得空泛，建议补充数字指标。",
        "suggestion_template": "优化示例：\n原文：「负责公司公众号运营」\n优化：「主导公司公众号运营，6个月内粉丝增长150%，阅读量提升200%，单篇最高阅读10w+」",
    },
    {
        "rule_id": "SHORT_DESCRIPTION", "category": "描述薄弱",
        "name": "项目/经历描述过短", "severity": "MEDIUM",
        "condition_json": '{"check_sections": ["experience", "project"], "min_chars_per_item": 50}',
        "description_template": "部分{section}描述过于简短（少于50字），建议展开描述具体工作内容、使用工具和取得成果。",
        "suggestion_template": "建议使用 STAR 法则展开描述：\n• Situation（背景）：项目/任务背景\n• Task（任务）：您承担的任务\n• Action（行动）：您采取的具体行动\n• Result（结果）：取得的成果（量化）",
    },
    {
        "rule_id": "VERB_REPETITION", "category": "描述薄弱",
        "name": "动词使用单调", "severity": "LOW",
        "condition_json": '{"repetitive_verbs": ["负责", "参与", "协助"], "min_repetition": 3}',
        "description_template": "简历中多次重复使用「负责」「参与」等动词，建议替换为更有力的动作动词。",
        "suggestion_template": "可替代的强力动词：\n• 主导、推动、策划、设计、开发、优化\n• 建立、整合、提升、突破、达成\n• 重构、改进、主导、统筹",
    },
    {
        "rule_id": "PUNCTUATION_MIX", "category": "格式问题",
        "name": "中英文标点混用", "severity": "LOW",
        "condition_json": '{"check_pattern": "[\\u3000-\\u303f].*[\\x00-\\x40]|[\\x00-\\x40].*[\\u3000-\\u303f]"}',
        "description_template": "简历中存在中英文标点混用情况，建议统一使用中文标点符号。",
        "suggestion_template": "注意区分：\n中文标点：，。、；：「」『』！？\n英文标点：, . ; : \" ' ! ?\n简历正文建议统一使用中文标点。",
    },
    {
        "rule_id": "DATE_FORMAT_INCONSISTENT", "category": "格式问题",
        "name": "日期格式不一致", "severity": "LOW",
        "condition_json": '{"check_pattern": "date_format"}',
        "description_template": "简历中的日期格式不统一（如混用2023.01、2023-01、2023年1月），建议统一格式。",
        "suggestion_template": "建议统一使用以下日期格式之一：\n• 2023.01 - 2024.06\n• 2023年1月 - 2024年6月",
    },
    {
        "rule_id": "TIME_OVERLAP", "category": "逻辑问题",
        "name": "工作经历时间重叠", "severity": "MEDIUM",
        "condition_json": '{"check_pattern": "date_overlap"}',
        "description_template": "部分工作经历时间区间存在重叠，请检查是否为笔误。",
        "suggestion_template": "请核实以下时间区间是否正确，必要时添加注释说明（如：兼职、实习与正式工作并行）。",
    },
    {
        "rule_id": "MISSING_CORE_KEYWORD", "category": "关键词缺失",
        "name": "缺少岗位核心技能关键词", "severity": "HIGH",
        "condition_json": '{"min_required_keyword_hit": 0.5}',
        "description_template": "目标岗位「{position}」的核心必备技能「{keyword}」未在简历中出现，您的简历可能被HR或ATS系统筛除。",
        "suggestion_template": "如果具备该技能，请在技能列表或经历描述中明确写出「{keyword}」。如果只是了解程度，可使用「了解{keyword}」「熟悉{keyword}」等表述。",
    },
    {
        "rule_id": "TOO_SHORT", "category": "篇幅问题",
        "name": "简历内容过短", "severity": "MEDIUM",
        "condition_json": '{"min_total_chars": 200}',
        "description_template": "简历总字数少于200字，信息量过少，难以让HR充分了解您的能力和经验。",
        "suggestion_template": "建议补充以下内容：\n1. 完整的教育背景（学校、专业、学历、毕业年份）\n2. 工作/实习/项目经历（每段至少3-5行）\n3. 技能清单\n4. 自我评价（2-3句）\n5. 荣誉/证书",
    },
    {
        "rule_id": "TOO_LONG", "category": "篇幅问题",
        "name": "简历内容过长", "severity": "LOW",
        "condition_json": '{"max_total_chars": 2000}',
        "description_template": "简历总字数超过2000字，建议精简至1-2页。HR平均浏览一份简历仅6秒，重点突出、简洁明了更有利。",
        "suggestion_template": "精简建议：\n1. 删除与目标岗位无关的经历\n2. 合并相似项目描述\n3. 删除超过5年的早期经历（应届生除外）\n4. 去掉不必要的个人爱好和信息",
    },
    {
        "rule_id": "EMPTY_SKILLS", "category": "信息缺失",
        "name": "技能列表为空或太少", "severity": "MEDIUM",
        "condition_json": '{"min_skills": 3}',
        "description_template": "简历中技能项少于3个，建议补充专业技能、工具、证书等，让HR了解您的技术栈。",
        "suggestion_template": "建议按类别列出技能：\n• 专业技能：XXX、XXX\n• 工具/软件：XXX、XXX\n• 语言能力：英语CET-6、普通话二级甲等\n• 证书：XXX资格证",
    },
    {
        "rule_id": "NO_HONORS", "category": "信息缺失",
        "name": "缺少荣誉/奖项/证书", "severity": "LOW",
        "condition_json": '{"has_section": ["荣誉", "奖项", "证书", "获奖"]}',
        "description_template": "简历中未提及任何荣誉、奖项或证书。如果有相关荣誉（奖学金、竞赛获奖、优秀员工等），建议补充。",
        "suggestion_template": "荣誉/证书示例格式：\n• 2023年 国家励志奖学金\n• 2022年 全国大学生数学建模竞赛 省级一等奖\n• 英语CET-6 580分\n• 腾讯云认证高级架构师",
    },
    {
        "rule_id": "EDUCATION_MISMATCH", "category": "信息缺失",
        "name": "学历与岗位要求不匹配", "severity": "MEDIUM",
        "condition_json": '{"compare_field": "education_required"}',
        "description_template": "目标岗位「{position}」通常要求{required_education}学历，您在简历中的学历信息可能不满足此要求。",
        "suggestion_template": "建议：\n1. 如果您的实际学历满足要求，请确保简历中清晰标注学历层次\n2. 如果学历不达标，可通过突出职业技能和项目经验来弥补\n3. 考虑在自我评价中说明学习能力和成长潜力",
    },
]

# 全局默认评分权重（当岗位未单独配置时使用）
DEFAULT_WEIGHTS = {
    "completeness": 0.20, "experience": 0.30, "skill": 0.20,
    "education": 0.15, "expression": 0.10, "format": 0.05,
}


# ==================== 初始化函数 ====================

def init_db(engine=None):
    """初始化数据库：创建所有表并导入种子数据"""
    if engine is None:
        engine = create_engine(settings.DATABASE_URL, echo=False)

    # 创建所有表
    Base.metadata.create_all(engine)
    logger.info("数据库表创建完成")

    with Session(engine) as db:
        # 检查是否已有数据（避免重复导入）
        existing = db.query(PositionCategory).count()
        if existing > 0:
            logger.info("种子数据已存在，跳过导入")
            return

        # 1. 创建管理员账号
        admin = User(
            email="admin@resume.com",
            username="admin",
            password_hash=hash_password("admin123"),
            role="admin",
        )
        test_user = User(
            email="test@resume.com",
            username="testuser",
            password_hash=hash_password("test123"),
            role="user",
        )
        db.add_all([admin, test_user])
        db.flush()
        logger.info("默认用户创建完成 (admin / testuser)")

        # 2. 导入岗位大类
        categories = []
        for cat_data in CATEGORIES:
            cat = PositionCategory(**cat_data)
            db.add(cat)
            categories.append(cat)
        db.flush()
        logger.info(f"岗位大类导入完成: {len(categories)} 个")

        # 3. 导入岗位 + 关键词 + 权重
        position_map = {}  # name -> Position obj
        for cat_idx, name, edu, exp_years in POSITIONS_DATA:
            pos = Position(
                category_id=categories[cat_idx].id,
                name=name,
                education_required=edu,
                experience_years=exp_years,
                description=f"{name}岗位描述",
            )
            db.add(pos)
            db.flush()
            position_map[name] = pos

            # 导入岗位关键词
            keywords = POSITION_KEYWORDS_DATA.get(name, [])
            for kw, kw_type, weight, required in keywords:
                pk = PositionKeyword(
                    position_id=pos.id,
                    keyword=kw,
                    keyword_type=kw_type,
                    weight=weight,
                    is_required=required,
                )
                db.add(pk)

            # 导入评分权重（按大类配置）
            cat_name = CATEGORIES[cat_idx]["name"]
            cat_weights = CATEGORY_WEIGHTS.get(cat_name, DEFAULT_WEIGHTS)
            for dim, w in cat_weights.items():
                sw = ScoringWeight(
                    position_id=pos.id,
                    dimension=dim,
                    weight=w,
                    threshold=60.0,
                )
                db.add(sw)

        logger.info(f"岗位导入完成: {len(position_map)} 个（含关键词与权重）")

        # 4. 导入缺陷规则
        for rule_data in DEFECT_RULES:
            rule = DefectRule(**rule_data)
            db.add(rule)
        logger.info(f"缺陷规则导入完成: {len(DEFECT_RULES)} 条")

        db.commit()
        logger.info("数据库初始化完成！")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("数据库初始化成功！")
