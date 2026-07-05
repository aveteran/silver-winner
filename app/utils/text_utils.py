"""文本处理工具"""
import re
import logging

try:
    import jieba
    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """通用文本清洗"""
    if not text:
        return ""
    # 去除多余空白
    text = re.sub(r'\s+', ' ', text)
    # 去除控制字符
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    # 统一换行
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    return text.strip()


def tokenize(text: str) -> list:
    """jieba分词"""
    if not text or not JIEBA_AVAILABLE:
        return text.split() if text else []
    return list(jieba.cut(text))


def extract_pattern(text: str, pattern: str) -> list:
    """正则提取，返回所有匹配组"""
    return re.findall(pattern, text)


def extract_first(text: str, pattern: str) -> str:
    """正则提取第一个匹配"""
    match = re.search(pattern, text)
    return match.group(0) if match else ""


# 常用正则模式
PATTERNS = {
    "phone": r'1[3-9]\d{9}',
    "email": r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    "chinese_name": r'[一-龥]{2,4}(?=\s|$|，|。|,|\.|\n)',
    "date_range": r'(\d{4}[年.\-/]\d{1,2})\s*[至\-~到]\s*(\d{4}[年.\-/]\d{1,2}|至今|现在)',
    "education": r'(博士|硕士|本科|专科|大专|高中|中专)',
    "school": r'(大学|学院|University|College)',
}


def count_chinese_chars(text: str) -> int:
    """统计中文字符数"""
    return len(re.findall(r'[一-龥]', text))


def count_english_words(text: str) -> int:
    """统计英文单词数"""
    return len(re.findall(r'[a-zA-Z]+', text))


def detect_punctuation_mix(text: str) -> bool:
    """检测中英文标点是否混用"""
    has_chinese_punct = bool(re.search(r'[　-〿＀-￯]', text))
    has_english_punct = bool(re.search(r'[!,\-\.:;\?]', text))
    return has_chinese_punct and has_english_punct


def count_quantified_sentences(text: str) -> int:
    """统计含量化数据的句子数"""
    sentences = re.split(r'[。！？\n]', text)
    count = 0
    for sent in sentences:
        if re.search(r'\d+', sent) and len(sent) > 10:
            count += 1
    return count
