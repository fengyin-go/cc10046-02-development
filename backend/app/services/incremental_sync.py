"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class IncrementalSyncService(BaseModuleService):
    MODULE = "incremental_sync"
    ENTITY = "同步水位"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["水位标识", "来源配置", "增量字段", "上次水位", "当前水位", "同步间隔", "覆盖策略", "下次同步"]
    REQUIRED_FIELDS = ["水位标识", "来源配置", "增量字段"]
    STATUS_ORDER = ["待启动", "同步中", "已同步", "同步中断"]
    ACTION_RULES = {"触发同步": "待启动", "重置水位": "同步中断"}
    NEGATIVE_ACTIONS = []
