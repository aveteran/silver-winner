"""FastAPI 应用入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from app.config import settings
from app.database.init_db import init_db
from app.api.deps import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理：启动时初始化数据库"""
    init_db(engine)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# 静态文件挂载
app.mount("/static", StaticFiles(directory="static"), name="static")

# 模板引擎
templates = Jinja2Templates(directory="templates")


# ==================== API 路由注册 ====================
from app.api.v1.auth import router as auth_router
from app.api.v1.resume import router as resume_router
from app.api.v1.position import router as position_router
from app.api.v1.admin import router as admin_router

app.include_router(auth_router, prefix="/api/v1")
app.include_router(resume_router, prefix="/api/v1")
app.include_router(position_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")


# ==================== 前端页面路由 ====================
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """首页"""
    return templates.TemplateResponse("index.html", {"request": request, "app_name": settings.APP_NAME})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """登录页"""
    return templates.TemplateResponse("auth/login.html", {"request": request, "app_name": settings.APP_NAME})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """注册页"""
    return templates.TemplateResponse("auth/register.html", {"request": request, "app_name": settings.APP_NAME})


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """上传页"""
    return templates.TemplateResponse("upload.html", {"request": request, "app_name": settings.APP_NAME})


@app.get("/report/{resume_id}", response_class=HTMLResponse)
async def report_page(request: Request, resume_id: int):
    """评估报告页"""
    return templates.TemplateResponse("report.html", {"request": request, "app_name": settings.APP_NAME})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """个人仪表板"""
    return templates.TemplateResponse("dashboard.html", {"request": request, "app_name": settings.APP_NAME})


@app.get("/positions", response_class=HTMLResponse)
async def positions_page(request: Request):
    """岗位库页"""
    return templates.TemplateResponse("positions.html", {"request": request, "app_name": settings.APP_NAME})


@app.get("/history", response_class=HTMLResponse)
async def history_page(request: Request):
    """评估记录页"""
    return templates.TemplateResponse("history.html", {"request": request, "app_name": settings.APP_NAME})


@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    """管理后台"""
    return templates.TemplateResponse("admin/index.html", {"request": request, "app_name": settings.APP_NAME})


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
