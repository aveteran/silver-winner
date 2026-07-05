"""文件解析器抽象基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ParseResult:
    """解析结果"""
    success: bool
    raw_text: str = ""
    error: str = ""
    page_count: int = 0
    metadata: dict = field(default_factory=dict)


class BaseParser(ABC):
    """文件解析器抽象基类"""

    @abstractmethod
    def parse(self, file_path: str) -> ParseResult:
        """解析文件，返回 ParseResult"""
        ...

    @abstractmethod
    def supported_extensions(self) -> list:
        """返回支持的文件扩展名列表"""
        ...
