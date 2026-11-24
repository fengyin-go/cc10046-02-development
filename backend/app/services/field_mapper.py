"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class FieldMapperService(BaseModuleService):
    MODULE = "field_mapper"
    ENTITY = "映射方案"
    OPERATION_TERM = "转换"
    LIST_FIELDS = ["方案标识", "来源字段", "目标字段", "转换函数", "默认取值", "映射版本", "适用站点", "依赖字段"]
    REQUIRED_FIELDS = ["方案标识", "来源字段", "目标字段"]
    STATUS_ORDER = ["草稿", "待校验", "已生效", "已停用"]
    ACTION_RULES = {"提交校验": "待校验", "启用映射": "已生效", "停用映射": "已停用"}
    NEGATIVE_ACTIONS = ["停用映射"]

    def domain_map_fields(self, source_data: dict, mapping_rules: list[dict]) -> dict:
        """根据映射规则将来源字段转换为目标字段。"""
        result: dict = {}
        for rule in mapping_rules:
            src_field = rule.get("source", "")
            tgt_field = rule.get("target", "")
            default = rule.get("default", "")
            transform = rule.get("transform", "")

            value = source_data.get(src_field, default)
            if transform == "upper":
                value = str(value).upper()
            elif transform == "lower":
                value = str(value).lower()
            elif transform == "int":
                try:
                    value = int(float(value))
                except (ValueError, TypeError):
                    value = 0
            result[tgt_field] = value
        return result

    def domain_coverage(
        self,
        records: list[dict],
        mapping_rules: list[dict] | None = None,
        key_fields: list[str] | None = None,
        threshold: float = 0.9,
    ) -> dict:
        """用映射后的采集记录计算关键字段覆盖率。

        实采到的 0 是有效值；默认取值补出来的 0 不算有效，并计入缺值。
        """
        from app.services.coverage_acceptance import coverage_service
        return coverage_service.domain_map_records(
            records,
            mapping_rules=mapping_rules,
            key_fields=key_fields,
            threshold=threshold,
        )["summary"]
