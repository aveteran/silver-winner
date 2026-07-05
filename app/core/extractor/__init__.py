"""信息抽取引擎：整合段落切分 + 关键词匹配"""
import json
import logging
from typing import Dict, Optional
from app.core.extractor.section_splitter import SectionSplitter, ResumeSections
from app.core.extractor.keyword_matcher import KeywordMatcher
from app.models.position import Position, PositionKeyword

logger = logging.getLogger(__name__)


def extract_resume_info(raw_text: str) -> ResumeSections:
    """从简历全文提取结构化信息"""
    splitter = SectionSplitter()
    sections = splitter.split(raw_text)
    logger.info(
        f"信息抽取完成: 姓名={sections.name}, "
        f"教育={len(sections.education)}条, "
        f"技能={len(sections.skills)}个, "
        f"工作={len(sections.work_experience)}条, "
        f"项目={len(sections.projects)}个"
    )
    return sections


def match_position_keywords(
    sections: ResumeSections,
    position: Position,
) -> Dict:
    """将简历内容与目标岗位关键词匹配"""
    if not position or not position.keywords:
        return {"total": 0, "hit": 0, "hit_rate": 0}

    matcher = KeywordMatcher(position.keywords)

    # 全文本匹配
    full_text = sections.raw_text

    result = matcher.match_all(full_text)
    logger.info(
        f"关键词匹配({position.name}): "
        f"{result['hit']}/{result['total']} = {result['hit_rate']:.0%}, "
        f"必备: {result['required_hit']}/{result['required_total']}"
    )
    return result


def sections_to_dict(sections: ResumeSections) -> Dict:
    """将 ResumeSections 序列化为可存储的字典"""
    from dataclasses import asdict
    d = asdict(sections)
    del d["raw_text"]
    return d


def sections_to_json(sections: ResumeSections) -> str:
    """序列化为JSON字符串"""
    return json.dumps(sections_to_dict(sections), ensure_ascii=False, indent=2)
