"""
认证与安全模块
JWT Token 生成/验证 + 密码哈希
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import settings

# 密码哈希上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码与哈希密码是否匹配"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str | int, extra_claims: dict[str, Any] | None = None) -> str:
    """生成 access_token（短期有效）"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    claims = {"sub": str(subject), "exp": expire, "type": "access"}
    if extra_claims:
        claims.update(extra_claims)
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | int) -> str:
    """生成 refresh_token（长期有效）"""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    claims = {"sub": str(subject), "exp": expire, "type": "refresh"}
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """解码并验证 JWT Token，返回 claims 字典"""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])


def verify_access_token(token: str) -> dict[str, Any] | None:
    """验证 access_token 并返回 claims，失败返回 None"""
    try:
        claims = decode_token(token)
        if claims.get("type") != "access":
            return None
        return claims
    except JWTError:
        return None


def verify_refresh_token(token: str) -> dict[str, Any] | None:
    """验证 refresh_token 并返回 claims，失败返回 None"""
    try:
        claims = decode_token(token)
        if claims.get("type") != "refresh":
            return None
        return claims
    except JWTError:
        return None
