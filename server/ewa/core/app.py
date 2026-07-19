"""妙喵私教 — FastAPI 应用工厂

三模块架构：管理后台 (admin) / Chrome 插件 (extension) / 网页 (site)

使用方式:
    from ewa.core import create_app
    app = create_app()
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from ewa.config import SITE_DB_PATH, SITE_SCHEMA_PATH
from ewa.core.middleware import SPAStaticFiles, configure_cors, create_rate_limit_middleware
from ewa.core.logging import setup_logging, create_request_logging_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：初始化日志、数据库、服务、后台任务。"""
    from ewa.website import SiteRepository, SiteService
    from ewa.admin import AdminRepository
    from ewa.extension.store import set_db_path

    print("妙喵私教 starting up...")

    db_path = app.state.site_db_path
    os.environ["EWA_SITE_DB_PATH"] = db_path

    # 初始化日志系统
    setup_logging(db_path)

    # 共享数据库路径
    set_db_path(db_path)
    app.state.admin_repository = AdminRepository(db_path)

    # 站点模块
    app.state.site_repository = SiteRepository(
        db_path=Path(db_path),
        schema_path=Path(app.state.site_schema_path),
    )
    app.state.site_repository.initialize()
    app.state.site_service = SiteService(app.state.site_repository)

    # 后台学习博主风格
    async def _learn_style_background():
        try:
            profile = app.state.site_repository.profile(app.state.default_slug)
            if profile:
                await app.state.site_service._learn_style(profile["id"])
        except Exception:
            pass
    import asyncio as _asyncio
    _asyncio.create_task(_learn_style_background())

    print(f"妙喵私教 ready. DB: {db_path}")
    yield
    print("妙喵私教 shutting down...")


def create_app(site_db_path: str | None = None) -> FastAPI:
    """创建 FastAPI 应用实例。

    Args:
        site_db_path: SQLite 数据库路径，默认从配置读取。
    """
    project_root = Path(__file__).resolve().parents[2]
    default_slug = os.getenv("NEXT_PUBLIC_SITE_SLUG", "miaomiao")

    app = FastAPI(
        title="妙喵私教",
        version="0.3.0",
        description="三模块架构 — 管理后台 · Chrome 插件 · 博主互动站",
        lifespan=lifespan,
    )

    # 状态初始化
    app.state.site_db_path = site_db_path or str(SITE_DB_PATH)
    app.state.site_schema_path = str(SITE_SCHEMA_PATH)
    app.state.default_slug = default_slug
    os.environ.setdefault("EWA_SITE_DB_PATH", app.state.site_db_path)

    # CORS
    configure_cors(app)

    # 请求日志中间件（在所有 CORS 处理后记录 API 请求）
    app.add_middleware(create_request_logging_middleware())

    # 请求限流
    if os.getenv("EWA_RATE_LIMIT", "1") != "0":
        app.add_middleware(create_rate_limit_middleware())

    # ═══ 注册路由 ═══════════════════════════════════════════

    # 🌐 网页模块
    from ewa.website.api import router as website_router
    app.include_router(website_router)

    # 🔌 插件模块
    from ewa.extension.ext_api import router as ext_router
    app.include_router(ext_router)
    from ewa.extension.lesson_api import router as lesson_router
    app.include_router(lesson_router)

    # 🛠 管理后台模块
    from ewa.admin.api import router as admin_router
    app.include_router(admin_router)

    # 💬 共创社区模块
    from ewa.community.api import router as community_router
    app.include_router(community_router)

    # 🎤 语音识别模块
    from ewa.speech import router as speech_router
    app.include_router(speech_router)

    # 健康检查
    @app.get("/health")
    async def health():
        repo = app.state.site_repository
        profile = repo.profile(default_slug)
        return {
            "status": "ok",
            "site": {"seeded": profile is not None},
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

    # ═══ 静态文件挂载 ═══════════════════════════════════════

    # 管理后台 SPA — 处理无尾斜杠的 /admin 请求
    @app.get("/admin")
    async def admin_redirect():
        from starlette.responses import RedirectResponse
        return RedirectResponse(url="/admin/")

    admin_dir = project_root / "ewa" / "admin" / "static"
    if admin_dir.exists():
        app.mount(
            "/admin/",
            SPAStaticFiles(directory=str(admin_dir), html=True),
            name="admin_spa",
        )

    # 前端网站静态产物
    frontend_dir = project_root / "frontend" / "dist"
    if frontend_dir.exists():
        app.mount(
            "/",
            SPAStaticFiles(directory=str(frontend_dir), html=True),
            name="frontend",
        )

    return app


# 模块级实例 — 延迟创建以支持循环导入
# run.py 中 uvicorn 引用 "ewa.api.main:app" 通过 api/main.py 提供
_app: FastAPI | None = None


def get_app() -> FastAPI:
    global _app
    if _app is None:
        _app = create_app()
    return _app


app = get_app()  # 首次导入时创建
