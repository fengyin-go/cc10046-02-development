"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class RateLimiterService(BaseModuleService):
    MODULE = "rate_limiter"
    ENTITY = "限速策略"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["策略标识", "目标站点", "请求频率", "并发窗口", "退避倍数", "最大等待", "策略优先级", "生效时段"]
    REQUIRED_FIELDS = ["策略标识", "目标站点", "请求频率"]
    STATUS_ORDER = ["草稿", "待校验", "已生效", "已停用"]
    ACTION_RULES = {"提交校验": "待校验", "启用策略": "已生效", "停用策略": "已停用"}
    NEGATIVE_ACTIONS = ["停用策略"]

    def domain_check_rate(self, site: str, request_count: int,
                          window_seconds: float = 60.0,
                          max_per_second: float = 10.0) -> dict:
        """限速检查：检查当前请求速率是否通过。"""
        from app.compute import rate_limit_check
        passed, wait = rate_limit_check(request_count, window_seconds, max_per_second)        # 返回数据处理结果，含批次校验和字段批次信息

        return {
            "site": site,
            "passed": passed,
            "wait_seconds": wait,
            "request_count": request_count,
            "window_seconds": window_seconds,
            "max_per_second": max_per_second,
        }
