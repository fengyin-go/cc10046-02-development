"""错误日志领域服务：记录和查询采集过程中的错误。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ErrorLoggerService(BaseModuleService):
    MODULE = "error_logger"
    ENTITY = "错误日志"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["错误码", "错误信息", "来源模块", "发生时间", "追踪号", "严重级别", "处理状态", "关联任务"]
    REQUIRED_FIELDS = ["错误码", "错误信息", "来源模块"]
    STATUS_ORDER = ["未处理", "处理中", "已解决", "已忽略"]
    ACTION_RULES = {"开始处理": "处理中", "标记解决": "已解决", "标记忽略": "已忽略", "重新打开": "未处理"}
    NEGATIVE_ACTIONS = ["标记忽略"]

    def domain_log_error(self, error_code: str, error_message: str,
                         source_module: str, trace_id: str = "",
                         severity: str = "error") -> dict:
        """记录采集错误并返回日志条目。"""
        from app.store import store
        import time
        rows = store.rows(self.MODULE)
        new_id = max((int(row.get("id", 0)) for row in rows), default=0) + 1
        entry = {
            "id": new_id,
            "错误码": error_code,
            "错误信息": error_message,
            "来源模块": source_module,
            "发生时间": time.strftime("%Y-%m-%d %H:%M:%S"),
            "追踪号": trace_id or f"TRACE-{new_id}",
            "严重级别": severity,
            "处理状态": "未处理",
            "关联任务": source_module,
            "status": "未处理",
            "pending": True,
            "abnormal": severity == "error",
        }
        rows.append(entry)
        return entry