"""简历相关 Pydantic 模型"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, field_serializer


class ResumeUploadResponse(BaseModel):
    """上传响应"""
    resume_id: int
    task_id: str = ""
    status: str = "pending"
    message: str = "文件上传成功，正在处理中"


class ResumeStatusResponse(BaseModel):
    """处理状态响应"""
    resume_id: int
    status: str  # pending / processing / completed / failed
    error: Optional[str] = None


class ScoringDataResponse(BaseModel):
    """评分数据响应"""
    total_score: float
    grade: str
    grade_description: str = ""
    dimension_scores: dict
    dimension_labels: dict
    weights_used: dict
    position_name: str = ""


class DefectItemResponse(BaseModel):
    """缺陷项响应"""
    id: int
    rule_id: str
    category: str
    severity: str
    description: str
    location: Optional[str] = None

    model_config = {"from_attributes": True}


class OptimizationItemResponse(BaseModel):
    """优化建议项响应"""
    id: int
    category: str
    title: str
    content: str
    original_text: Optional[str] = None
    improved_example: Optional[str] = None

    model_config = {"from_attributes": True}


class ResumeReportResponse(BaseModel):
    """完整评估报告响应"""
    resume_id: int
    filename: str
    position_name: Optional[str] = None
    status: str
    scoring: Optional[ScoringDataResponse] = None
    defects: List[DefectItemResponse] = []
    optimizations: List[OptimizationItemResponse] = []
    defect_summary: dict = {}
    created_at: Optional[str] = None


class PositionResponse(BaseModel):
    """岗位响应"""
    id: int
    category_name: Optional[str] = None
    name: str
    description: Optional[str] = None
    education_required: Optional[str] = None
    experience_years: Optional[int] = None

    model_config = {"from_attributes": True}
