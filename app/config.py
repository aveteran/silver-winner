"""
应用配置中心
所有配置项集中管理，敏感信息通过 .env 文件加载
"""
from typing import List
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用全局配置"""

    # 基础信息
    APP_NAME: str = "简历智能评估与优化系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # 数据库
    DATABASE_URL: str = "sqlite:///./data/resume_system.db"

    # JWT 认证
    SECRET_KEY: str = "change-this-to-a-random-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 文件上传
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".doc"]

    # 可选 LLM 增强（默认关闭）
    LLM_ENABLED: bool = False
    LLM_API_KEY: str = ""
    LLM_API_URL: str = ""
    LLM_MODEL: str = ""

    # 分页
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# 确保必要目录存在
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path("./data").mkdir(parents=True, exist_ok=True)
