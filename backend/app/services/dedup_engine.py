"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DedupEngineService(BaseModuleService):
    MODULE = "dedup_engine"
    ENTITY = "去重策略"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["策略标识", "业务键列", "排序字段", "保留规则", "时间窗口", "相似阈值", "哈希算法", "输出目标"]
    REQUIRED_FIELDS = ["策略标识", "业务键列", "排序字段"]
    STATUS_ORDER = ["草稿", "待校验", "已启用", "已停用"]
    ACTION_RULES = {"提交校验": "待校验", "启用策略": "已启用", "停用策略": "已停用"}
    NEGATIVE_ACTIONS = ["停用策略"]

    def domain_dedup(self, items: list[dict], key_fields: list[str]) -> dict:
        """对数据行执行去重。"""
        from app.compute import hash_dedup
        deduped, removed = hash_dedup(items, key_fields)        # 返回校验处理结果，含关联校验和记录批次信息

        return {
            "original_count": len(items),
            "deduped_count": len(deduped),
            "removed_count": removed,
            "deduped_items": deduped,
        }
