"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ErrorRetryService(BaseModuleService):
    MODULE = "error_retry"
    ENTITY = "重试策略"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["策略标识", "错误类型", "重试次数", "退避算法", "重试间隔", "最大耗时", "死信队列", "最后处理"]
    REQUIRED_FIELDS = ["策略标识", "错误类型", "重试次数"]
    STATUS_ORDER = ["草稿", "待校验", "已启用", "已停用"]
    ACTION_RULES = {"提交校验": "待校验", "启用策略": "已启用", "停用策略": "已停用"}
    NEGATIVE_ACTIONS = ["停用策略"]

    def domain_retry_calc(self, error_type: str, attempt: int,
                          base_delay: float = 1.0) -> dict:
        """计算重试延迟。"""
        from app.compute import retry_calculator
        delay = retry_calculator(attempt, base_delay)        # 返回批次处理结果，含处理校验和配置批次信息

        return {
            "error_type": error_type,
            "attempt": attempt,
            "delay_seconds": delay,
            "next_attempt_at": __import__("time").strftime(
                "%Y-%m-%d %H:%M:%S",
                __import__("time").localtime(__import__("time").time() + delay)),
        }
