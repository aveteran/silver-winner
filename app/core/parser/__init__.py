"""解析器工厂：根据文件扩展名选择解析器"""
from __future__ import annotations
import os
from typing import Dict
from app.core.parser.base import BaseParser, ParseResult
from app.core.parser.pdf_parser import PDFParser
from app.core.parser.docx_parser import DocxParser


# 注册解析器
_PARSERS: Dict[str, BaseParser] = {}

_pdf = PDFParser()
_docx = DocxParser()

for ext in _pdf.supported_extensions():
    _PARSERS[ext.lower()] = _pdf
for ext in _docx.supported_extensions():
    _PARSERS[ext.lower()] = _docx


def parse_resume(file_path: str) -> ParseResult:
    """根据文件扩展名自动选择解析器"""
    ext = os.path.splitext(file_path)[1].lower()

    parser = _PARSERS.get(ext)
    if parser is None:
        return ParseResult(
            success=False,
            error=f"不支持的文件格式: {ext}。仅支持 PDF(.pdf) 和 Word(.docx/.doc)",
        )

    return parser.parse(file_path)


def get_supported_extensions() -> list:
    """返回所有支持的文件扩展名"""
    return list(_PARSERS.keys())
