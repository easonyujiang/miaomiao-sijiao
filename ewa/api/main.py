"""妙喵私教 — FastAPI 后端服务

为博主互动站和 Chrome 插件提供 API：
- /api/site/*   博主网站数据
- /api/ext/*    插件视频注册/问答
- /api/lesson/* 课程加载/答题评分
"""

from __future__ import annotations

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from ewa.config import SITE_DB_PATH, SITE_SCHEMA_PATH
from ewa.site import SiteRepository, SiteService
from ewa.site.api import router as site_router
from ewa.api.ext import router as ext_router
from ewa.api.lesson import router as lesson_router


class SPAStaticFiles(StaticFiles):
    """Serve index.html for client-side routes such as /blog/:slug."""

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
            if response.status_code != 404:
                return response
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
        return await super().get_response("index.html", scope)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("妙喵私教 starting up...")
    db_path = app.state.site_db_path
    os.environ["EWA_SITE_DB_PATH"] = db_path  # lesson 模块与 site 共用 db
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
    project_root = Path(__file__).resolve().parents[2]
    app = FastAPI(
        title="妙喵私教",
        version="0.1.0",
        description="把教学视频变成一对一私教 — 博主互动站 + Chrome 插件后端",
        lifespan=lifespan,
    )
    app.state.site_db_path = site_db_path or str(SITE_DB_PATH)
    app.state.site_schema_path = str(SITE_SCHEMA_PATH)
    os.environ.setdefault("EWA_SITE_DB_PATH", app.state.site_db_path)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(site_router)
    app.include_router(ext_router)
    app.include_router(lesson_router)

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

    frontend_dir = project_root / "frontend" / "dist"
    if frontend_dir.exists():
        app.mount("/", SPAStaticFiles(directory=str(frontend_dir), html=True), name="frontend")

    return app


app = create_app()
