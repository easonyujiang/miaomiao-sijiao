"""妙喵私教 — 核心框架层

提供 FastAPI 应用工厂、CORS 中间件、SPA 静态文件服务、日志等基础能力。
"""

# 延迟导入以避免循环依赖 — 使用者应从 ewa.core.app 直接导入
# from ewa.core.app import create_app, app

__all__: list[str] = []
