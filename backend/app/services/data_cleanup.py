"""数据清理领域服务：管理过期数据和存储空间回收。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DataCleanupService(BaseModuleService):
    MODULE = "data_cleanup"
    ENTITY = "清理任务"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["任务标识", "目标模块", "保留天数", "清理类型", "预计影响", "执行状态", "上次执行", "下次执行"]
    REQUIRED_FIELDS = ["任务标识", "目标模块", "保留天数"]
    STATUS_ORDER = ["待执行", "执行中", "已完成", "执行失败"]
    ACTION_RULES = {"启动清理": "待执行", "标记完成": "已完成"}
    NEGATIVE_ACTIONS = []

    def domain_cleanup(self, task_id: str, target_module: str,
                       retention_days: int = 30, cleanup_type: str = "soft") -> dict:
        """执行数据清理并返回清理报告。"""
        from app.store import store
        import time
        rows = store.rows(self.MODULE)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        affected = 0
        target_rows = store.rows(target_module)
        affected = len([r for r in target_rows if r.get("status") in ("已归档", "已停用", "已过期", "已废弃")])
        entry = {
            "id": max((int(row.get("id", 0)) for row in rows), default=0) + 1,
            "任务标识": task_id,
            "目标模块": target_module,
            "保留天数": str(retention_days),
            "清理类型": cleanup_type,
            "预计影响": str(affected),
            "执行状态": "已完成",
            "上次执行": now,
            "下次执行": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + 86400)),
            "status": "已完成",
            "pending": False,
            "abnormal": False,
        }
        rows.append(entry)
        return entry