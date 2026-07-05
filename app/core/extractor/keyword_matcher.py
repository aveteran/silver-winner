"""关键词匹配器：在简历文本中匹配岗位关键词"""
import re
from typing import List, Dict, Tuple
from app.models.position import PositionKeyword


class KeywordMatcher:
    """岗位关键词匹配器"""

    def __init__(self, keywords: List[PositionKeyword]):
        """
        Args:
            keywords: 岗位对应的关键词ORM对象列表
        """
        self.keywords = keywords
        self.required_keywords = [kw for kw in keywords if kw.is_required]
        self.optional_keywords = [kw for kw in keywords if not kw.is_required]

    def match_all(self, text: str) -> Dict[str, any]:
        """
        在文本中匹配所有关键词
        Returns:
            {
                "total": 总关键词数,
                "hit": 命中数,
                "hit_rate": 命中率,
                "required_total": 必备关键词数,
                "required_hit": 必备命中数,
                "required_hit_rate": 必备命中率,
                "hit_list": [命中的关键词],
                "miss_list": [未命中的关键词],
                "miss_required": [未命中的必备关键词],
            }
        """
        text_lower = text.lower()
        hit_list = []
        miss_list = []
        required_hit = 0

        for kw in self.keywords:
            keyword = kw.keyword.lower()
            # 不区分大小写的模糊匹配
            if keyword in text_lower:
                hit_list.append({
                    "keyword": kw.keyword,
                    "type": kw.keyword_type,
                    "weight": kw.weight,
                    "is_required": kw.is_required,
                })
                if kw.is_required:
                    required_hit += 1
            else:
                miss_list.append({
                    "keyword": kw.keyword,
                    "type": kw.keyword_type,
                    "weight": kw.weight,
                    "is_required": kw.is_required,
                })

        miss_required = [kw for kw in miss_list if kw["is_required"]]

        total = len(self.keywords)
        required_total = len(self.required_keywords)

        return {
            "total": total,
            "hit": len(hit_list),
            "hit_rate": len(hit_list) / total if total > 0 else 0,
            "required_total": required_total,
            "required_hit": required_hit,
            "required_hit_rate": required_hit / required_total if required_total > 0 else 1.0,
            "hit_list": hit_list,
            "miss_list": miss_list,
            "miss_required": miss_required,
        }

    def get_missing_required(self, text: str) -> List[str]:
        """获取未命中的必备关键词名称列表"""
        result = self.match_all(text)
        return [kw["keyword"] for kw in result["miss_required"]]

    def get_hit_keywords(self, text: str) -> List[str]:
        """获取命中的关键词名称列表"""
        result = self.match_all(text)
        return [kw["keyword"] for kw in result["hit_list"]]
