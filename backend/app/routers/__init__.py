"""业务路由汇总：所有模块共用一套资源路由，由领域服务完成分派。"""
from __future__ import annotations

from app.routers import coverage
from app.routers import resource
from app.routers import chains

# 固定路径的路由（coverage / chains）必须排在通用资源路由 resource 之前，
# 否则 /api/{module}/{entry_id} 会截走它们的路径段。
ROUTERS = [coverage, resource, chains]
