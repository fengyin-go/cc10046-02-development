"""会话管理领域服务：管理采集会话生命周期。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class SessionManagerService(BaseModuleService):
    MODULE = "session_manager"
    ENTITY = "采集会话"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["会话标识", "关联配置", "会话类型", "创建时间", "最后活跃", "过期时间", "会话状态", "请求计数"]
    REQUIRED_FIELDS = ["会话标识", "关联配置", "会话类型"]
    STATUS_ORDER = ["活跃", "空闲", "已过期", "已关闭"]
    ACTION_RULES = {"激活会话": "活跃", "关闭会话": "已关闭", "续期会话": "活跃"}
    NEGATIVE_ACTIONS = ["关闭会话"]

    def domain_create_session(self, session_id: str, config_name: str,
                              session_type: str = "http") -> dict:
        """创建新的采集会话。"""
        from app.store import store
        import time
        rows = store.rows(self.MODULE)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "id": max((int(row.get("id", 0)) for row in rows), default=0) + 1,
            "会话标识": session_id,
            "关联配置": config_name,
            "会话类型": session_type,
            "创建时间": now,
            "最后活跃": now,
            "过期时间": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time() + 3600)),
            "会话状态": "活跃",
            "请求计数": "0",
            "status": "活跃",
            "pending": True,
            "abnormal": False,
        }
        rows.append(entry)
        return entry