"""妙喵私教 — FastAPI 应用工厂

创建并配置 FastAPI 应用实例，注册所有路由和中间件。

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：初始化数据库、注册服务到 app.state。"""
    from ewa.site import SiteRepository, SiteService
    from ewa.demo.store import set_db_path

    print("妙喵私教 starting up...")
    db_path = app.state.site_db_path
    os.environ["EWA_SITE_DB_PATH"] = db_path  # lesson 模块与 site 共用 db

    # P1-5: 显式注入 db_path（lesson 模块优先使用此路径）
    set_db_path(db_path)

    app.state.site_repository = SiteRepository(
        db_path=Path(db_path),
        schema_path=Path(app.state.site_schema_path),
    )
    app.state.site_repository.initialize()
    app.state.site_service = SiteService(app.state.site_repository)

    print(f"妙喵私教 ready. DB: {db_path}")
    yield
    print("妙喵私教 shutting down...")


def create_app(site_db_path: str | None = None) -> FastAPI:
    """创建 FastAPI 应用实例。

    Args:
        site_db_path: SQLite 数据库路径，默认从配置读取。用于测试时注入临时数据库。
    """
    project_root = Path(__file__).resolve().parents[2]

    app = FastAPI(
        title="妙喵私教",
        version="0.2.0",
        description="把教学视频变成一对一私教 — 博主互动站 + Chrome 插件后端",
        lifespan=lifespan,
    )

    # 状态初始化
    app.state.site_db_path = site_db_path or str(SITE_DB_PATH)
    app.state.site_schema_path = str(SITE_SCHEMA_PATH)
    os.environ.setdefault("EWA_SITE_DB_PATH", app.state.site_db_path)

    # CORS
    configure_cors(app)

    # 请求限流（对 LLM 调用端点更严格）
    if os.getenv("EWA_RATE_LIMIT", "1") != "0":
        app.add_middleware(create_rate_limit_middleware())

    # 注册路由
    from ewa.site.api import router as site_router
    from ewa.api.ext import router as ext_router
    from ewa.api.lesson import router as lesson_router

    app.include_router(site_router)
    app.include_router(ext_router)
    app.include_router(lesson_router)

    # 健康检查
    @app.get("/health")
    async def health():
        repo = app.state.site_repository
        return {
            "status": "ok",
            "site": {
                "profiles": len(repo.projects("profile_ashley")) > 0,
            },
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

    # 托管前端静态导出产物
    frontend_dir = project_root / "frontend" / "dist"
    if frontend_dir.exists():
        app.mount(
            "/",
            SPAStaticFiles(directory=str(frontend_dir), html=True),
            name="frontend",
        )

    return app


# 模块级实例（供 uvicorn 直接引用）
app = create_app()
