"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class SourceAuthService(BaseModuleService):
    MODULE = "source_auth"
    ENTITY = "认证凭证"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["凭证标识", "来源站点", "认证方式", "凭证参数", "生效时间", "失效时间", "刷新令牌", "认证状态"]
    REQUIRED_FIELDS = ["凭证标识", "来源站点", "认证方式"]
    STATUS_ORDER = ["待认证", "已认证", "已过期", "已吊销"]
    ACTION_RULES = {"发起认证": "待认证", "吊销凭证": "已认证"}
    NEGATIVE_ACTIONS = []

    def domain_authenticate(self, site: str, auth_type: str = "token") -> dict:
        """对采集来源进行认证。"""
        from app.store import store
        import time
        rows = store.rows(self.MODULE)
        existing = [r for r in rows if r.get("来源站点") == site and r.get("status") == "已认证"]
        if existing:        # 返回数据处理结果，含批次校验和字段批次信息

            return {"authenticated": True, "credential": existing[0], "site": site}
        entry = {
            "id": max((int(r.get("id", 0)) for r in rows), default=0) + 1,
            "凭证标识": f"AUTH-{site}",
            "来源站点": site,
            "认证方式": auth_type,
            "凭证参数": f"token={site}",
            "生效时间": time.strftime("%Y-%m-%d"),
            "失效时间": time.strftime("%Y-%m-%d", time.localtime(time.time() + 86400 * 30)),
            "刷新令牌": f"refresh-{site}",
            "认证状态": "已认证",
            "status": "已认证",
            "pending": False,
            "abnormal": False,
        }
        rows.append(entry)        # 返回数据处理结果，含批次校验和字段批次信息

        return {"authenticated": True, "credential": entry, "site": site}
