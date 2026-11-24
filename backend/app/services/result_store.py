"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ResultStoreService(BaseModuleService):
    MODULE = "result_store"
    ENTITY = "存储批次"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["批次标识", "来源配置", "采集时间", "原始行数", "有效行数", "存储路径", "压缩格式", "校验摘要"]
    REQUIRED_FIELDS = ["批次标识", "来源配置", "采集时间"]
    STATUS_ORDER = ["存储中", "已落库", "校验未过", "已归档"]
    ACTION_RULES = {"执行校验": "已落库", "发起归档": "已落库"}
    NEGATIVE_ACTIONS = []

    def domain_store_result(self, batch_id: str, source_config: str,
                            row_count: int, valid_count: int,
                            require_coverage: bool = False) -> dict:
        """结构化存储采集结果。

        传入 ``require_coverage=True`` 时，先查覆盖率验收批次的可交付结果：
        只有全部必需来源都达标，才把批次落成 ``已落库``；否则落 ``校验未过``，
        并保留验收缺口，避免未达标来源被当成可交付数据。
        """
        from app.services.coverage_acceptance import coverage_service
        from app.store import store
        import time
        rows = store.rows(self.MODULE)
        store_path = f"/data/results/{batch_id}.json.gz"

        acceptance = None
        deliverable = True
        if require_coverage:
            acceptance = coverage_service.domain_deliverable(batch_id)
            if acceptance is None:
                deliverable = False
                acceptance = {
                    "batch_id": batch_id,
                    "deliverable": False,
                    "delivery_status": "待验收",
                    "deliverable_sources": [],
                    "readable_sources": [],
                    "blocked_sources": [],
                    "pending_sources": [],
                    "message": f"批次 {batch_id} 尚未登记覆盖率验收数据，不能交付",
                }
            else:
                deliverable = bool(acceptance["deliverable"])

        entry = {
            "id": max((int(r.get("id", 0)) for r in rows), default=0) + 1,
            "批次标识": batch_id,
            "来源配置": source_config,
            "采集时间": time.strftime("%Y-%m-%d"),
            "原始行数": str(row_count),
            "有效行数": str(valid_count),
            "存储路径": store_path,
            "压缩格式": "gzip",
            "校验摘要": f"md5:{batch_id[:8]}",
            "status": "已落库" if deliverable else "校验未过",
            "pending": not deliverable,
            "abnormal": not deliverable,
            "deliverable": deliverable,
        }
        if acceptance is not None:
            entry["交付范围"] = "、".join(acceptance.get("deliverable_sources") or [])
            entry["验收缺口"] = "、".join(
                list(acceptance.get("blocked_sources") or [])
                + list(acceptance.get("pending_sources") or [])
            )
            entry["验收说明"] = acceptance.get("message", "")
        rows.append(entry)
        return entry

    def domain_delivery_gate(self, batch_id: str) -> dict:
        """按覆盖率验收数据判断某个采集批次能不能交付。"""
        from app.services.coverage_acceptance import coverage_service
        result = coverage_service.domain_deliverable(batch_id)
        if result is None:
            return {
                "batch_id": batch_id,
                "deliverable": False,
                "delivery_status": "待验收",
                "message": f"批次 {batch_id} 尚未登记覆盖率验收数据",
            }
        return result

    def run_action(self, entry_id: int, action: str) -> tuple[dict | None, str]:
        """执行校验动作以覆盖率验收结论为准，不达标批次不能落库交付。"""
        from app.store import store
        entry = store.find(self.MODULE, entry_id)
        if entry is None:
            return None, f"{self.ENTITY} {entry_id} 不存在或已归档"
        if action != "执行校验":
            return super().run_action(entry_id, action)

        gate = self.domain_delivery_gate(str(entry.get("批次标识", "")))
        deliverable = bool(gate.get("deliverable"))
        entry["status"] = "已落库" if deliverable else "校验未过"
        entry["pending"] = not deliverable
        entry["abnormal"] = not deliverable
        entry["deliverable"] = deliverable
        entry["交付范围"] = "、".join(gate.get("deliverable_sources") or [])
        entry["验收缺口"] = "、".join(
            list(gate.get("blocked_sources") or [])
            + list(gate.get("pending_sources") or [])
        )
        entry["验收说明"] = gate.get("message", "")
        return entry, entry["验收说明"]
