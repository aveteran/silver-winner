"""简历管理接口：上传、状态查询、评分、缺陷、优化建议、报告、导出"""
import os
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.api.schemas.resume import (
    ResumeUploadResponse, ResumeStatusResponse,
    ScoringDataResponse, DefectItemResponse, OptimizationItemResponse,
    ResumeReportResponse,
)
from app.models.resume import Resume
from app.models.position import Position, PositionCategory
from app.models.user import User
from app.models.scoring import ScoringResult
from app.models.defect import ResumeDefect, OptimizationSuggestion
from app.services.resume_service import (
    save_uploaded_file, create_resume_record, process_resume, get_processing_result
)
from app.config import settings
from app.core.scorer.weight_manager import GRADE_DESCRIPTIONS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resumes", tags=["简历管理"])


def _get_user_resume(resume_id: int, user: User, db: Session) -> Resume:
    """获取用户拥有的简历，否则抛出异常"""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    if resume.user_id != user.id and user.role != "admin":
        raise HTTPException(status_code=403, detail="无权访问此简历")
    return resume


@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    position_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传简历文件（PDF/DOCX），后台异步处理"""
    # 验证文件扩展名
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {ext}。仅支持 PDF(.pdf) 和 Word(.docx/.doc)",
        )

    # 验证文件大小
    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=400, detail=f"文件过大，最大支持10MB")

    # 验证岗位ID（如果提供）
    position = None
    if position_id:
        position = db.query(Position).filter(Position.id == position_id).first()
        if not position:
            raise HTTPException(status_code=400, detail=f"岗位不存在: {position_id}")

    # 保存文件
    try:
        stored_path = save_uploaded_file(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    # 创建简历记录
    file_type = ext.lstrip('.')
    resume = create_resume_record(
        db=db,
        user=current_user,
        original_filename=file.filename,
        file_path=stored_path,
        file_type=file_type,
        position_id=position_id,
    )

    # 后台异步处理
    background_tasks.add_task(_process_resume_bg, resume.id, position_id, db)

    return ResumeUploadResponse(
        resume_id=resume.id,
        task_id=str(resume.id),
        status="pending",
    )


def _process_resume_bg(resume_id: int, position_id: Optional[int], db: Session):
    """后台任务：处理简历"""
    from app.api.deps import engine
    from sqlalchemy.orm import Session as NewSession

    with NewSession(engine) as session:
        try:
            resume = session.query(Resume).filter(Resume.id == resume_id).first()
            if not resume:
                return

            position = None
            if position_id:
                position = session.query(Position).filter(Position.id == position_id).first()

            process_resume(resume, position, session)
        except Exception as e:
            logger.error(f"后台处理简历失败: {resume_id}, 错误: {e}")
            try:
                resume = session.query(Resume).filter(Resume.id == resume_id).first()
                if resume:
                    resume.parse_status = "failed"
                    resume.parse_error = str(e)
                    session.commit()
            except Exception:
                pass


@router.get("/{resume_id}/status", response_model=ResumeStatusResponse)
def get_resume_status(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查询简历处理状态（前端轮询用）"""
    resume = _get_user_resume(resume_id, current_user, db)
    return ResumeStatusResponse(
        resume_id=resume.id,
        status=resume.parse_status,
        error=resume.parse_error,
    )


@router.get("/{resume_id}/score", response_model=ScoringDataResponse)
def get_resume_score(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取简历评分结果"""
    resume = _get_user_resume(resume_id, current_user, db)
    if resume.parse_status != "completed":
        raise HTTPException(status_code=400, detail=f"简历尚未处理完成，当前状态: {resume.parse_status}")

    scoring = db.query(ScoringResult).filter(ScoringResult.resume_id == resume_id).first()
    if not scoring:
        raise HTTPException(status_code=404, detail="评分结果不存在")

    return ScoringDataResponse(
        total_score=scoring.total_score,
        grade=scoring.grade,
        grade_description=GRADE_DESCRIPTIONS.get(scoring.grade, ""),
        dimension_scores={
            "completeness": scoring.completeness_score,
            "experience": scoring.experience_score,
            "skill": scoring.skill_score,
            "education": scoring.education_score,
            "expression": scoring.expression_score,
            "format": scoring.format_score,
        },
        dimension_labels={
            "completeness": "内容完整度",
            "experience": "经历匹配度",
            "skill": "技能覆盖度",
            "education": "教育匹配度",
            "expression": "表达质量",
            "format": "格式规范性",
        },
        weights_used={},
        position_name=resume.target_position.name if resume.target_position else "",
    )


@router.get("/{resume_id}/defects", response_model=List[DefectItemResponse])
def get_resume_defects(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取简历缺陷列表"""
    resume = _get_user_resume(resume_id, current_user, db)
    if resume.parse_status != "completed":
        raise HTTPException(status_code=400, detail="简历尚未处理完成")

    defects = db.query(ResumeDefect).filter(ResumeDefect.resume_id == resume_id).all()
    return defects


@router.get("/{resume_id}/optimizations", response_model=List[OptimizationItemResponse])
def get_resume_optimizations(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取优化建议列表"""
    resume = _get_user_resume(resume_id, current_user, db)
    if resume.parse_status != "completed":
        raise HTTPException(status_code=400, detail="简历尚未处理完成")

    suggestions = db.query(OptimizationSuggestion).filter(
        OptimizationSuggestion.resume_id == resume_id
    ).all()
    return suggestions


@router.get("/{resume_id}/report", response_model=ResumeReportResponse)
def get_resume_report(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取完整评估报告（评分+缺陷+建议汇总）"""
    resume = _get_user_resume(resume_id, current_user, db)

    result = get_processing_result(resume, db)
    if not result:
        raise HTTPException(status_code=400, detail="报告不可用，简历可能尚未处理完成")

    scoring = result["scoring"]
    defects = result["defects"]
    optimizations = result["optimizations"]

    # 缺陷汇总
    high = len([d for d in defects if d.severity == "HIGH"])
    medium = len([d for d in defects if d.severity == "MEDIUM"])
    low = len([d for d in defects if d.severity == "LOW"])

    return ResumeReportResponse(
        resume_id=resume.id,
        filename=resume.original_filename,
        position_name=resume.target_position.name if resume.target_position else None,
        status=resume.parse_status,
        scoring=ScoringDataResponse(
            total_score=scoring.total_score,
            grade=scoring.grade,
            grade_description=GRADE_DESCRIPTIONS.get(scoring.grade, ""),
            dimension_scores={
                "completeness": scoring.completeness_score,
                "experience": scoring.experience_score,
                "skill": scoring.skill_score,
                "education": scoring.education_score,
                "expression": scoring.expression_score,
                "format": scoring.format_score,
            },
            dimension_labels={
                "completeness": "内容完整度",
                "experience": "经历匹配度",
                "skill": "技能覆盖度",
                "education": "教育匹配度",
                "expression": "表达质量",
                "format": "格式规范性",
            },
            weights_used={},
            position_name=resume.target_position.name if resume.target_position else "",
        ),
        defects=[DefectItemResponse(
            id=d.id, rule_id=d.rule_id, category=d.category,
            severity=d.severity, description=d.description, location=d.location
        ) for d in defects],
        optimizations=[OptimizationItemResponse(
            id=o.id, category=o.category, title=o.title,
            content=o.content, original_text=o.original_text,
            improved_example=o.improved_example,
        ) for o in optimizations],
        defect_summary={"high": high, "medium": medium, "low": low, "total": len(defects)},
        created_at=resume.created_at.isoformat() if resume.created_at else None,
    )


@router.get("/{resume_id}/export/pdf")
def export_resume_pdf(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """导出简历评估报告为PDF"""
    resume = _get_user_resume(resume_id, current_user, db)
    result = get_processing_result(resume, db)
    if not result:
        raise HTTPException(status_code=400, detail="报告不可用")

    from app.core.exporter.pdf_exporter import export_report_html

    # 构建报告数据
    scoring = result["scoring"]
    defects = result["defects"]
    optimizations = result["optimizations"]

    report_data = {
        "filename": resume.original_filename,
        "position_name": resume.target_position.name if resume.target_position else "通用",
        "scoring": {
            "total_score": scoring.total_score,
            "grade": scoring.grade,
            "grade_description": GRADE_DESCRIPTIONS.get(scoring.grade, ""),
            "dimension_scores": {
                "completeness": scoring.completeness_score,
                "experience": scoring.experience_score,
                "skill": scoring.skill_score,
                "education": scoring.education_score,
                "expression": scoring.expression_score,
                "format": scoring.format_score,
            },
            "dimension_labels": {
                "completeness": "内容完整度",
                "experience": "经历匹配度",
                "skill": "技能覆盖度",
                "education": "教育匹配度",
                "expression": "表达质量",
                "format": "格式规范性",
            },
        },
        "defects": [
            {"category": d.category, "severity": d.severity, "description": d.description, "location": d.location}
            for d in defects
        ],
        "optimizations": [
            {"title": o.title, "content": o.content, "original_text": o.original_text or "", "improved_example": o.improved_example or ""}
            for o in optimizations
        ],
    }

    try:
        from app.core.exporter.pdf_exporter import export_report_pdf
        pdf_bytes = export_report_pdf(report_data)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=resume_report_{resume_id}.pdf"},
        )
    except RuntimeError:
        # WeasyPrint 不可用时，返回HTML格式
        html = export_report_html(report_data)
        return Response(
            content=html.encode("utf-8"),
            media_type="text/html; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename=resume_report_{resume_id}.html"},
        )
