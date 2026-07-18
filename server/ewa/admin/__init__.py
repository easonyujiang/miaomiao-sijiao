"""管理后台模块

提供：
- /api/admin/* — RESTful CRUD API（20 表）
- /admin — 独立管理 SPA 界面
- 审计日志记录与查询
"""

from ewa.admin.repository import AdminRepository

__all__ = ["AdminRepository"]
