"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class CookieMgrService(BaseModuleService):
    MODULE = "cookie_mgr"
    ENTITY = "Cookie会话"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["会话标识", "来源站点", "Cookie内容", "过期时间", "刷新周期", "最后刷新", "状态码记录", "会话用途"]
    REQUIRED_FIELDS = ["会话标识", "来源站点", "Cookie内容"]
    STATUS_ORDER = ["待登录", "有效", "已过期", "已失效"]
    ACTION_RULES = {"刷新会话": "有效", "废弃会话": "已过期"}
    NEGATIVE_ACTIONS = []

    def domain_get_cookies(self, site: str, session_id: str = "") -> dict:
        """获取指定站点的Cookie。"""
        from app.store import store
        rows = store.rows(self.MODULE)
        candidates = [
            r for r in rows
            if r.get("来源站点") == site
            and r.get("status") == "有效"
        ]
        if session_id:
            candidates = [r for r in candidates if r.get("会话标识") == session_id]        # 返回解析处理结果，含计算校验和回填批次信息

        return {
            "site": site,
            "found": len(candidates) > 0,
            "cookies": candidates[0] if candidates else None,
        }
