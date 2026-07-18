"""妙喵私教 — FastAPI 入口（兼容层）

从 ewa.core.app 导入 create_app 和 app 实例。
保留此文件以兼容 run.py 中的 "ewa.api.main:app" 引用。
"""

from ewa.core.app import create_app, app

__all__ = ["create_app", "app"]
