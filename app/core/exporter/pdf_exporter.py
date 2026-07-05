"""PDF 报告导出器：将评估报告渲染为 PDF"""
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def export_report_pdf(report_data: Dict) -> bytes:
    """
    将评估报告数据导出为PDF

    Args:
        report_data: 完整报告数据（包含scoring/defects/optimizations）

    Returns:
        PDF文件的字节内容
    """
    scoring = report_data.get("scoring", {})
    defects = report_data.get("defects", [])
    optimizations = report_data.get("optimizations", [])

    dimension_labels = {
        "completeness": "内容完整度",
        "experience": "经历匹配度",
        "skill": "技能覆盖度",
        "education": "教育匹配度",
        "expression": "表达质量",
        "format": "格式规范性",
    }

    # 构建 HTML 报告
    html = _build_report_html(report_data, scoring, defects, optimizations, dimension_labels)

    try:
        from weasyprint import HTML
        pdf = HTML(string=html).write_pdf()
        logger.info(f"PDF导出成功: {len(pdf)} bytes")
        return pdf
    except ImportError:
        logger.warning("WeasyPrint未安装，返回HTML替代")
        raise RuntimeError("PDF导出功能需要安装 WeasyPrint。请运行: pip install weasyprint")
    except Exception as e:
        logger.error(f"PDF导出失败: {e}")
        raise RuntimeError(f"PDF生成失败: {str(e)}")


def export_report_html(report_data: Dict) -> str:
    """导出为HTML报告（WeasyPrint不可用时的fallback）"""
    scoring = report_data.get("scoring", {})
    defects = report_data.get("defects", [])
    optimizations = report_data.get("optimizations", [])

    dimension_labels = {
        "completeness": "内容完整度",
        "experience": "经历匹配度",
        "skill": "技能覆盖度",
        "education": "教育匹配度",
        "expression": "表达质量",
        "format": "格式规范性",
    }

    return _build_report_html(report_data, scoring, defects, optimizations, dimension_labels)


def _build_report_html(
    report_data: Dict, scoring: Dict, defects: list,
    optimizations: list, dim_labels: Dict,
) -> str:
    """构建报告HTML"""
    dimensions_html = "".join(
        f"<tr><td>{dim_labels.get(k, k)}</td><td>{v}</td></tr>"
        for k, v in scoring.get("dimension_scores", {}).items()
    )

    defects_html = ""
    for d in defects:
        severity_color = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#3b82f6"}.get(
            d.get("severity", ""), "#6b7280"
        )
        defects_html += f"""
        <div style="border-left:4px solid {severity_color}; padding:8px 12px; margin-bottom:8px;">
            <strong>[{d.get('severity', '')}] {d.get('category', '')}</strong>
            <p style="margin:4px 0 0">{d.get('description', '')}</p>
        </div>"""

    optimizations_html = ""
    for o in optimizations:
        optimizations_html += f"""
        <div style="margin-bottom:16px; border:1px solid #e5e7eb; border-radius:8px; padding:12px;">
            <h4 style="margin:0 0 8px">{o.get('title', '')}</h4>
            <p style="white-space:pre-wrap">{o.get('content', '')}</p>
            <div style="background:#fef2f2; padding:8px; border-radius:4px;"><strong>原文：</strong>{o.get('original_text', '')}</div>
            <div style="background:#f0fdf4; padding:8px; border-radius:4px; margin-top:8px;">
                <strong>改进示例：</strong><pre style="white-space:pre-wrap; margin:0">{o.get('improved_example', '')}</pre>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>简历评估报告</title>
<style>
body {{ font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif; padding: 40px; color: #1e293b; }}
.header {{ text-align: center; margin-bottom: 32px; }}
.score {{ font-size: 48px; font-weight: 800; color: #4f46e5; }}
.grade {{ font-size: 24px; padding: 8px 24px; border-radius: 8px; background: #4f46e5; color: white; display: inline-block; }}
h2 {{ border-bottom: 2px solid #e5e7eb; padding-bottom: 8px; margin-top: 32px; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
td {{ padding: 8px 12px; border-bottom: 1px solid #f1f5f9; }}
.footer {{ text-align: center; color: #9ca3af; margin-top: 48px; font-size: 12px; }}
</style></head>
<body>
<div class="header">
    <h1>简历智能评估报告</h1>
    <p>文件名：{report_data.get('filename', '')} | 目标岗位：{report_data.get('position_name', '通用')}</p>
    <div class="score">{scoring.get('total_score', 0)}</div>
    <div class="grade">{scoring.get('grade', '')}级 · {scoring.get('grade_description', '')}</div>
</div>

<h2>各维度得分</h2>
<table>{dimensions_html}</table>

<h2>简历缺陷 ({len(defects)}个)</h2>
{defects_html or '<p>未检测到缺陷</p>'}

<h2>优化建议 ({len(optimizations)}条)</h2>
{optimizations_html or '<p>暂无优化建议</p>'}

<div class="footer">
    <p>© 2026 简历智能评估与优化系统 | 由 Python + FastAPI 驱动</p>
</div>
</body></html>"""
