"""PDF简历解析器（基于 pdfplumber）"""
import logging
from app.core.parser.base import BaseParser, ParseResult

logger = logging.getLogger(__name__)


class PDFParser(BaseParser):
    """PDF文件解析器"""

    def supported_extensions(self) -> list:
        return [".pdf"]

    def parse(self, file_path: str) -> ParseResult:
        try:
            import pdfplumber

            all_text = []
            page_count = 0

            with pdfplumber.open(file_path) as pdf:
                page_count = len(pdf.pages)
                for page in pdf.pages:
                    # 提取文本
                    text = page.extract_text()
                    if text:
                        all_text.append(text)

                    # 提取表格
                    tables = page.extract_tables()
                    for table in tables:
                        if table:
                            table_text = self._format_table(table)
                            if table_text:
                                all_text.append(table_text)

            raw_text = "\n".join(all_text)
            raw_text = self._clean_text(raw_text)

            if not raw_text.strip():
                return ParseResult(
                    success=False,
                    error="PDF文件中未提取到文本内容，可能是扫描件或图片型PDF",
                    page_count=page_count,
                )

            logger.info(f"PDF解析成功: {file_path}, {page_count}页, {len(raw_text)}字符")
            return ParseResult(
                success=True,
                raw_text=raw_text,
                page_count=page_count,
                metadata={"file_path": file_path, "type": "pdf"},
            )

        except ImportError:
            return ParseResult(success=False, error="pdfplumber库未安装")
        except Exception as e:
            logger.error(f"PDF解析失败: {file_path}, 错误: {e}")
            return ParseResult(success=False, error=f"PDF解析失败: {str(e)}")

    def _format_table(self, table: list) -> str:
        """将表格转换为文本"""
        rows = []
        for row in table:
            if row:
                cells = [str(cell).strip() if cell else "" for cell in row]
                rows.append(" | ".join(c for c in cells if c))
        return "\n".join(rows)

    def _clean_text(self, text: str) -> str:
        """清洗PDF提取文本"""
        import re

        # 去除多余空行（保留单个换行）
        text = re.sub(r'\n{3,}', '\n\n', text)
        # 去除行尾多余空格
        text = re.sub(r' +\n', '\n', text)
        # 统一全角/半角标点
        text = text.replace('，', ',').replace('。', '.')
        # 修复PDF常见乱码
        text = text.replace('\x00', '').replace('\r', '\n')

        return text.strip()
