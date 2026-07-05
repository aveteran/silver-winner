"""认证接口：注册、登录、刷新Token"""
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.api.schemas.auth import (
    UserRegisterRequest, UserLoginRequest,
    TokenResponse, RefreshTokenRequest, UserResponse, ApiResponse,
)
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, verify_refresh_token
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/register", response_model=ApiResponse)
def register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """用户注册"""
    # 检查邮箱是否已注册
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该邮箱已被注册")

    # 检查用户名是否已占用
    existing_username = db.query(User).filter(User.username == req.username).first()
    if existing_username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该用户名已被占用")

    # 创建用户
    user = User(
        email=req.email,
        username=req.username,
        password_hash=hash_password(req.password),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return ApiResponse(message="注册成功", data={"user_id": user.id})


@router.post("/login", response_model=TokenResponse)
def login(req: UserLoginRequest, db: Session = Depends(get_db)):
    """用户登录，返回 access_token + refresh_token"""
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账户已被禁用")

    # 更新最后登录时间
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    # 生成双Token
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(req: RefreshTokenRequest):
    """使用 refresh_token 刷新 access_token"""
    claims = verify_refresh_token(req.refresh_token)
    if claims is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="refresh_token无效或已过期")

    user_id = claims.get("sub")
    new_access_token = create_access_token(user_id)
    new_refresh_token = create_refresh_token(user_id)
    return TokenResponse(access_token=new_access_token, refresh_token=new_refresh_token)


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return current_user
