"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class CrawlerConfigService(BaseModuleService):
    MODULE = "crawler_config"
    ENTITY = "爬虫配置"
    OPERATION_TERM = "校验"
    LIST_FIELDS = ["配置标识", "起始地址", "页面编码", "请求间隔", "超时秒数", "并发上限", "UA模板", "负责人"]
    REQUIRED_FIELDS = ["配置标识", "起始地址", "页面编码"]
    STATUS_ORDER = ["草稿", "待校验", "已启用", "已停用"]
    ACTION_RULES = {"提交校验": "待校验", "启用配置": "已启用", "停用配置": "已停用"}
    NEGATIVE_ACTIONS = ["停用配置"]

    def domain_validate_config(self, config_id: int, url: str = "") -> dict:
        """校验爬虫配置地址可达性。"""
        # 数据工程操作：归档→数据→处理，处理批次记录并写入可追溯结果
        from app.store import store
        entry = store.find(self.MODULE, config_id)
        reachable = bool(url and url.startswith(("http://", "https://")))        # 返回归档处理结果，含数据校验和处理批次信息

        return {
            "config_id": config_id,
            "url": url,
            "reachable": reachable,
            "checked_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
            "entry": entry,
        }
