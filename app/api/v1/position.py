"""岗位库接口"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.schemas.resume import PositionResponse
from app.models.position import Position, PositionCategory
from app.models.user import User

router = APIRouter(prefix="/positions", tags=["岗位库"])


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    """获取岗位大类列表"""
    categories = db.query(PositionCategory).order_by(PositionCategory.sort_order).all()
    return [
        {"id": c.id, "name": c.name, "description": c.description}
        for c in categories
    ]


@router.get("", response_model=List[PositionResponse])
def get_positions(
    category_id: int = Query(None, description="按大类筛选"),
    keyword: str = Query(None, description="搜索关键词"),
    db: Session = Depends(get_db),
):
    """获取岗位列表（支持按类别筛选和搜索）"""
    query = db.query(Position).filter(Position.is_active == True)

    if category_id:
        query = query.filter(Position.category_id == category_id)

    if keyword:
        query = query.filter(Position.name.contains(keyword))

    positions = query.order_by(Position.name).all()

    result = []
    for p in positions:
        result.append(PositionResponse(
            id=p.id,
            category_name=p.category.name if p.category else None,
            name=p.name,
            description=p.description,
            education_required=p.education_required,
            experience_years=p.experience_years,
        ))

    return result


@router.get("/{position_id}", response_model=PositionResponse)
def get_position(position_id: int, db: Session = Depends(get_db)):
    """获取岗位详情"""
    position = db.query(Position).filter(Position.id == position_id).first()
    if not position:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return PositionResponse(
        id=position.id,
        category_name=position.category.name if position.category else None,
        name=position.name,
        description=position.description,
        education_required=position.education_required,
        experience_years=position.experience_years,
    )
