"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class CrawlScheduleService(BaseModuleService):
    MODULE = "crawl_schedule"
    ENTITY = "调度任务"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["任务标识", "关联配置", "调度周期", "起始水位", "截止水位", "分片策略", "上次执行", "下次执行"]
    REQUIRED_FIELDS = ["任务标识", "关联配置", "调度周期"]
    STATUS_ORDER = ["待启动", "运行中", "已完成", "调度失败"]
    ACTION_RULES = {"启动调度": "待启动", "取消调度": "调度失败"}
    NEGATIVE_ACTIONS = []

    def domain_create_schedule(self, config_name: str, period: str = "daily") -> dict:
        """生成采集调度计划。"""
        from app.store import store
        import time
        rows = store.rows(self.MODULE)
        task_id = f"SCHED-{max((int(r.get('id', 0)) for r in rows), default=0) + 1}"
        plan = {
            "task_id": task_id,
            "config_name": config_name,
            "period": period,
            "shard_count": 4,
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "watermark_start": "2026-01-01",
            "watermark_end": time.strftime("%Y-%m-%d"),
        }
        return plan
