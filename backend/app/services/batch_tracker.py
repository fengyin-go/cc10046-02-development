"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class BatchTrackerService(BaseModuleService):
    MODULE = "batch_tracker"
    ENTITY = "采集批次"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["批次标识", "调度任务", "开始时间", "结束时间", "采集总数", "失败行数", "水位标记", "批次状态"]
    REQUIRED_FIELDS = ["批次标识", "调度任务", "开始时间"]
    STATUS_ORDER = ["执行中", "部分成功", "全部成功", "采集失败"]
    ACTION_RULES = {"重采失败行": "部分成功", "标记完成": "全部成功"}
    NEGATIVE_ACTIONS = []

    def domain_track_batch(self, batch_id: str, schedule_id: str) -> dict:
        """追踪采集批次执行状态。"""
        from app.store import store
        import time
        rows = store.rows(self.MODULE)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "id": max((int(r.get("id", 0)) for r in rows), default=0) + 1,
            "批次标识": batch_id,
            "调度任务": schedule_id,
            "开始时间": now,
            "结束时间": None,
            "采集总数": "0",
            "失败行数": "0",
            "水位标记": now,
            "批次状态": "执行中",
            "status": "执行中",
            "pending": True,
            "abnormal": False,
        }
        rows.append(entry)
        return entry
