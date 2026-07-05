"""简历处理服务：编排解析→抽取→评分→缺陷→优化的完整流程"""
import json
import os
import logging
from typing import Optional, Dict
from sqlalchemy.orm import Session
from app.config import settings
from app.core.parser import parse_resume
from app.core.extractor import extract_resume_info, match_position_keywords, sections_to_json
from app.core.scorer.engine import calculate_score, ScoringReport
from app.core.defect.rules import run_defect_rules, DefectReport
from app.core.optimizer.generator import generate_optimizations, OptimizationReport
from app.models.resume import Resume
from app.models.position import Position
from app.models.scoring import ScoringResult
from app.models.defect import DefectRule, ResumeDefect, OptimizationSuggestion
from app.models.user import User

logger = logging.getLogger(__name__)


class ResumeProcessingError(Exception):
    """简历处理异常"""
    pass


def process_resume(
    resume: Resume,
    position: Optional[Position],
    db: Session,
) -> Dict:
    """
    处理单个简历的完整流程：
    1. 解析文件
    2. 提取信息
    3. 关键词匹配
    4. 评分
    5. 缺陷检测
    6. 优化建议生成

    Returns:
        {
            "resume": Resume,
            "sections": ResumeSections,
            "keyword_result": Dict,
            "scoring": ScoringReport,
            "defects": DefectReport,
            "optimizations": OptimizationReport,
        }
    """
    # Step 1: 解析文件
    logger.info(f"开始处理简历: {resume.original_filename}")
    parse_result = parse_resume(resume.file_path)
    if not parse_result.success:
        resume.parse_status = "failed"
        resume.parse_error = parse_result.error
        db.commit()
        raise ResumeProcessingError(parse_result.error)

    resume.raw_text = parse_result.raw_text
    resume.parse_status = "processing"
    db.commit()

    # Step 2: 信息抽取
    sections = extract_resume_info(parse_result.raw_text)
    resume.structured_data = sections_to_json(sections)
    db.commit()

    # Step 3: 关键词匹配
    keyword_result = {}
    if position and position.keywords:
        keyword_result = match_position_keywords(sections, position)

    # Step 4: 评分
    scoring_report = calculate_score(sections, position, keyword_result)

    # 保存评分结果
    scoring_result = ScoringResult(
        resume_id=resume.id,
        total_score=scoring_report.total_score,
        completeness_score=scoring_report.dimension_scores.get("completeness", 0),
        experience_score=scoring_report.dimension_scores.get("experience", 0),
        skill_score=scoring_report.dimension_scores.get("skill", 0),
        education_score=scoring_report.dimension_scores.get("education", 0),
        expression_score=scoring_report.dimension_scores.get("expression", 0),
        format_score=scoring_report.dimension_scores.get("format", 0),
        grade=scoring_report.grade,
    )
    db.add(scoring_result)
    db.flush()

    # Step 5: 缺陷检测
    rules = db.query(DefectRule).filter(DefectRule.is_active == True).all()
    defect_report = run_defect_rules(sections, rules, position, keyword_result)

    # 保存缺陷记录
    for d in defect_report.defects:
        defect_record = ResumeDefect(
            resume_id=resume.id,
            rule_id=d.rule_id,
            category=d.category,
            severity=d.severity,
            description=d.description,
            location=d.location,
        )
        db.add(defect_record)
    db.flush()

    # Step 6: 生成优化建议
    opt_report = generate_optimizations(defect_report.defects, sections, position)

    # 保存优化建议
    for item in opt_report.items:
        suggestion = OptimizationSuggestion(
            resume_id=resume.id,
            category=item.category,
            title=item.title,
            content=item.content,
            original_text=item.original_text,
            improved_example=item.improved_example,
        )
        db.add(suggestion)

    # 更新简历状态
    resume.parse_status = "completed"
    db.commit()

    logger.info(
        f"简历处理完成: 得分={scoring_report.total_score}, "
        f"等级={scoring_report.grade}, "
        f"缺陷={defect_report.total}个, "
        f"建议={opt_report.total}条"
    )

    return {
        "resume": resume,
        "sections": sections,
        "keyword_result": keyword_result,
        "scoring": scoring_report,
        "defects": defect_report,
        "optimizations": opt_report,
    }


def save_uploaded_file(file_content: bytes, original_filename: str) -> str:
    """保存上传文件到磁盘，返回存储路径"""
    import uuid
    ext = os.path.splitext(original_filename)[1]
    stored_name = f"{uuid.uuid4().hex}{ext}"
    stored_path = os.path.join(settings.UPLOAD_DIR, stored_name)

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    with open(stored_path, "wb") as f:
        f.write(file_content)

    return stored_path


def create_resume_record(
    db: Session,
    user: User,
    original_filename: str,
    file_path: str,
    file_type: str,
    position_id: Optional[int] = None,
) -> Resume:
    """创建简历数据库记录"""
    resume = Resume(
        user_id=user.id,
        original_filename=original_filename,
        file_path=file_path,
        file_type=file_type,
        target_position_id=position_id,
        parse_status="pending",
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)
    return resume


def get_processing_result(resume: Resume, db: Session) -> Optional[Dict]:
    """获取已完成处理的简历结果"""
    if resume.parse_status != "completed":
        return None

    scoring = db.query(ScoringResult).filter(
        ScoringResult.resume_id == resume.id
    ).first()

    defects = db.query(ResumeDefect).filter(
        ResumeDefect.resume_id == resume.id
    ).all()

    optimizations = db.query(OptimizationSuggestion).filter(
        OptimizationSuggestion.resume_id == resume.id
    ).all()

    if not scoring:
        return None

    return {
        "resume": resume,
        "scoring": scoring,
        "defects": defects,
        "optimizations": optimizations,
    }
