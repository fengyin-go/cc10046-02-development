"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class DataValidatorService(BaseModuleService):
    MODULE = "data_validator"
    ENTITY = "校验规则"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["规则标识", "校验字段", "校验类型", "校验参数", "失败动作", "阻断阈值", "采样比例", "上次执行"]
    REQUIRED_FIELDS = ["规则标识", "校验字段", "校验类型"]
    STATUS_ORDER = ["草稿", "待校验", "已启用", "已停用"]
    ACTION_RULES = {"提交校验": "待校验", "启用规则": "已启用", "停用规则": "已停用"}
    NEGATIVE_ACTIONS = ["停用规则"]
