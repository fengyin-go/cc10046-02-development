"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class ExtractionTemplateService(BaseModuleService):
    MODULE = "extraction_template"
    ENTITY = "抽取模板"
    OPERATION_TERM = "去重"
    LIST_FIELDS = ["模板标识", "适用站点", "列表选择器", "分页参数", "详情链接", "去重字段", "增量字段", "输出格式"]
    REQUIRED_FIELDS = ["模板标识", "适用站点", "列表选择器"]
    STATUS_ORDER = ["草稿", "待校验", "已发布", "已废弃"]
    ACTION_RULES = {"提交校验": "待校验", "发布模板": "已发布", "废弃模板": "已废弃"}
    NEGATIVE_ACTIONS = []
