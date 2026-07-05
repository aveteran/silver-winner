"""认证相关 Pydantic 请求/响应模型"""
from datetime import datetime
from typing import Optional, Dict, List, Any, Union
from pydantic import BaseModel, field_validator, field_serializer
import re


class UserRegisterRequest(BaseModel):
    """用户注册请求"""
    email: str
    username: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, v):
            raise ValueError("邮箱格式不正确")
        return v.lower()

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 2 or len(v) > 30:
            raise ValueError("用户名长度需在2-30个字符之间")
        return v.strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("密码长度至少6位")
        return v


class UserLoginRequest(BaseModel):
    """用户登录请求"""
    email: str
    password: str


class TokenResponse(BaseModel):
    """Token 响应"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """刷新Token请求"""
    refresh_token: str


class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    email: str
    username: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = {"from_attributes": True}

    @field_serializer("created_at", "last_login")
    @classmethod
    def serialize_datetime(cls, v: Optional[datetime]) -> Optional[str]:
        if v is None:
            return None
        return v.isoformat()


class ApiResponse(BaseModel):
    """通用API响应"""
    code: int = 200
    message: str = "success"
    data: Optional[Any] = None
