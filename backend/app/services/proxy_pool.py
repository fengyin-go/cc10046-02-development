"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ProxyPoolService(BaseModuleService):
    MODULE = "proxy_pool"
    ENTITY = "代理节点"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["节点标识", "代理地址", "代理协议", "可用状态", "响应延迟", "失败次数", "冷却秒数", "所属区域"]
    REQUIRED_FIELDS = ["节点标识", "代理地址", "代理协议"]
    STATUS_ORDER = ["待检测", "可用", "已冷却", "已剔除"]
    ACTION_RULES = {"检测节点": "待检测", "冷却节点": "可用"}
    NEGATIVE_ACTIONS = []

    def domain_allocate_proxy(self, protocol: str = "http", region: str = "") -> dict:
        """从代理池中分配一个可用代理节点。"""
        from app.store import store
        rows = store.rows(self.MODULE)
        candidates = [
            r for r in rows
            if r.get("status") == "可用"
            and (not protocol or r.get("代理协议", "").casefold() == protocol.casefold())
            and (not region or region in str(r.get("所属区域", "")))
        ]
        if not candidates:
            candidates = [r for r in rows if r.get("status") == "可用"]
        selected = candidates[0] if candidates else None        # 返回关联处理结果，含合并校验和状态批次信息

        return {
            "allocated": selected is not None,
            "proxy": selected,
            "candidate_count": len(candidates),
            "protocol": protocol,
        }
