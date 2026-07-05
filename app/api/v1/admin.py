"""管理后台接口：岗位管理、规则管理、关键词导入、系统统计"""
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_admin
from app.models.position import Position, PositionCategory, PositionKeyword, ScoringWeight
from app.models.defect import DefectRule
from app.models.user import User
from app.models.resume import Resume
from app.models.scoring import ScoringResult
from app.models.history import HistoryRecord

router = APIRouter(prefix="/admin", tags=["管理后台"])


# ==================== Pydantic 请求模型 ====================

class CreatePositionRequest(BaseModel):
    name: str
    category_id: int
    description: str = ""
    education_required: str = ""
    experience_years: int = 0


class UpdatePositionRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    education_required: Optional[str] = None
    experience_years: Optional[int] = None
    is_active: Optional[bool] = None


class AddKeywordRequest(BaseModel):
    keyword: str
    keyword_type: str = "skill"
    weight: float = 0.5
    is_required: bool = False


class UpdateRuleRequest(BaseModel):
    is_active: Optional[bool] = None
    severity: Optional[str] = None
    description_template: Optional[str] = None
    suggestion_template: Optional[str] = None


# ==================== 岗位管理 ====================

@router.post("/positions")
def create_position(
    req: CreatePositionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """新增岗位"""
    pos = Position(
        category_id=req.category_id, name=req.name,
        description=req.description, education_required=req.education_required,
        experience_years=req.experience_years,
    )
    db.add(pos)
    db.commit()
    db.refresh(pos)
    return {"message": "创建成功", "position_id": pos.id}


@router.put("/positions/{position_id}")
def update_position(
    position_id: int,
    req: UpdatePositionRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """编辑岗位"""
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="岗位不存在")
    if req.name is not None: pos.name = req.name
    if req.description is not None: pos.description = req.description
    if req.education_required is not None: pos.education_required = req.education_required
    if req.experience_years is not None: pos.experience_years = req.experience_years
    if req.is_active is not None: pos.is_active = req.is_active
    db.commit()
    return {"message": "更新成功"}


@router.delete("/positions/{position_id}")
def delete_position(
    position_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """删除岗位"""
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="岗位不存在")
    db.delete(pos)
    db.commit()
    return {"message": "删除成功"}


# ==================== 关键词管理 ====================

@router.post("/positions/{position_id}/keywords")
def add_keyword(
    position_id: int,
    req: AddKeywordRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """为岗位添加关键词"""
    pos = db.query(Position).filter(Position.id == position_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="岗位不存在")
    kw = PositionKeyword(
        position_id=position_id, keyword=req.keyword,
        keyword_type=req.keyword_type, weight=req.weight, is_required=req.is_required,
    )
    db.add(kw)
    db.commit()
    return {"message": "添加成功", "keyword_id": kw.id}


@router.delete("/keywords/{keyword_id}")
def delete_keyword(
    keyword_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """删除关键词"""
    kw = db.query(PositionKeyword).filter(PositionKeyword.id == keyword_id).first()
    if not kw:
        raise HTTPException(status_code=404, detail="关键词不存在")
    db.delete(kw)
    db.commit()
    return {"message": "删除成功"}


# ==================== 缺陷规则管理 ====================

@router.get("/rules")
def get_rules(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """获取所有缺陷规则"""
    rules = db.query(DefectRule).all()
    return [
        {
            "id": r.id, "rule_id": r.rule_id, "category": r.category,
            "name": r.name, "severity": r.severity,
            "condition_json": r.condition_json,
            "description_template": r.description_template,
            "suggestion_template": r.suggestion_template,
            "is_active": r.is_active,
        }
        for r in rules
    ]


@router.put("/rules/{rule_id}")
def update_rule(
    rule_id: int,
    req: UpdateRuleRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """更新缺陷规则"""
    rule = db.query(DefectRule).filter(DefectRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="规则不存在")
    if req.is_active is not None: rule.is_active = req.is_active
    if req.severity is not None: rule.severity = req.severity
    if req.description_template is not None: rule.description_template = req.description_template
    if req.suggestion_template is not None: rule.suggestion_template = req.suggestion_template
    db.commit()
    return {"message": "更新成功"}


# ==================== 系统统计 ====================

@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    """获取系统统计数据"""
    total_users = db.query(User).count()
    total_resumes = db.query(Resume).count()
    completed_resumes = db.query(Resume).filter(Resume.parse_status == "completed").count()
    failed_resumes = db.query(Resume).filter(Resume.parse_status == "failed").count()
    total_positions = db.query(Position).count()
    active_rules = db.query(DefectRule).filter(DefectRule.is_active == True).count()

    # 平均分
    from sqlalchemy import func
    avg_score = db.query(func.avg(ScoringResult.total_score)).scalar() or 0

    return {
        "users": total_users,
        "resumes": {"total": total_resumes, "completed": completed_resumes, "failed": failed_resumes},
        "positions": total_positions,
        "active_rules": active_rules,
        "avg_score": round(avg_score, 1),
    }
