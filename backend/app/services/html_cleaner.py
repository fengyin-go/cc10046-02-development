"""__NAME__领域服务：字段、状态和动作来自业务配置，数据处理骨架由基类复用。"""
from __future__ import annotations

from app.services.base import BaseModuleService


class HtmlCleanerService(BaseModuleService):
    MODULE = "html_cleaner"
    ENTITY = "清洗模板"
    OPERATION_TERM = "采集"
    LIST_FIELDS = ["模板标识", "适用站点", "标签过滤", "属性保留", "文本规整", "编码检测", "空白处理", "实体转义"]
    REQUIRED_FIELDS = ["模板标识", "适用站点", "标签过滤"]
    STATUS_ORDER = ["草稿", "待校验", "已启用", "已停用"]
    ACTION_RULES = {"提交校验": "待校验", "启用模板": "已启用", "停用模板": "已停用"}
    NEGATIVE_ACTIONS = ["停用模板"]

    def domain_clean_html(self, html_content: str, template_id: int = 0) -> dict:
        """清洗HTML内容，移除脚本和样式标签，规整空白。"""
        import re
        cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<!--.*?-->', '', cleaned, flags=re.DOTALL)
        cleaned = re.sub(r'<[^>]+>', ' ', cleaned)
        cleaned = re.sub(r'&nbsp;', ' ', cleaned)
        cleaned = re.sub(r'&amp;', '&', cleaned)
        cleaned = re.sub(r'&lt;', '<', cleaned)
        cleaned = re.sub(r'&gt;', '>', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()        # 返回采集处理结果，含查询校验和回填批次信息

        return {
            "template_id": template_id,
            "cleaned_text": cleaned,
            "original_length": len(html_content),
            "cleaned_length": len(cleaned),
        }
