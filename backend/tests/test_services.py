"""18个领域服务业务方法测试。"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.crawler_config import CrawlerConfigService
from app.services.crawl_schedule import CrawlScheduleService
from app.services.batch_tracker import BatchTrackerService
from app.services.result_store import ResultStoreService
from app.services.parser_rule import ParserRuleService
from app.services.field_mapper import FieldMapperService
from app.services.html_cleaner import HtmlCleanerService
from app.services.dedup_engine import DedupEngineService
from app.services.proxy_pool import ProxyPoolService
from app.services.rate_limiter import RateLimiterService
from app.services.error_retry import ErrorRetryService
from app.services.error_logger import ErrorLoggerService
from app.services.cookie_mgr import CookieMgrService
from app.services.source_auth import SourceAuthService
from app.services.session_manager import SessionManagerService
from app.services.export_channel import ExportChannelService
from app.services.crawl_audit import CrawlAuditService
from app.services.data_cleanup import DataCleanupService


def test_crawler_config_validate():
    svc = CrawlerConfigService()
    result = svc.domain_validate_config(1, "https://example.com")
    assert result["config_id"] == 1
    assert result["reachable"] is True

def test_crawl_schedule_create():
    svc = CrawlScheduleService()
    result = svc.domain_create_schedule("test-config")
    assert result["config_name"] == "test-config"
    assert result["period"] == "daily"
    assert result["shard_count"] == 4

def test_batch_tracker_track():
    svc = BatchTrackerService()
    result = svc.domain_track_batch("B-TEST-1", "SCHED-1")
    assert result["批次标识"] == "B-TEST-1"
    assert result["status"] == "执行中"

def test_result_store_store():
    svc = ResultStoreService()
    result = svc.domain_store_result("B-TEST-2", "cfg1", 200, 180)
    assert result["批次标识"] == "B-TEST-2"
    assert result["原始行数"] == "200"
    assert result["有效行数"] == "180"

def test_parser_rule_parse():
    svc = ParserRuleService()
    html = "<html><body><h1>Title</h1><p>Content here</p></body></html>"
    result = svc.domain_parse_html(html)
    assert result["field_count"] >= 1

def test_field_mapper_map():
    svc = FieldMapperService()
    source = {"name": "Alice", "count": "42"}
    rules = [
        {"source": "name", "target": "title", "default": "", "transform": ""},
        {"source": "count", "target": "total", "default": "0", "transform": "int"},
    ]
    result = svc.domain_map_fields(source, rules)
    assert result["title"] == "Alice"
    assert result["total"] == 42

def test_html_cleaner_clean():
    svc = HtmlCleanerService()
    html = "<html><body><p>Hello</p><script>alert(1)</script></body></html>"
    result = svc.domain_clean_html(html)
    assert "Hello" in result["cleaned_text"]
    assert "alert" not in result["cleaned_text"]
    assert result["cleaned_length"] < result["original_length"]

def test_dedup_engine_dedup():
    svc = DedupEngineService()
    items = [{"a": 1}, {"a": 1}, {"a": 2}]
    result = svc.domain_dedup(items, ["a"])
    assert result["original_count"] == 3
    assert result["deduped_count"] == 2
    assert result["removed_count"] == 1

def test_proxy_pool_allocate():
    svc = ProxyPoolService()
    result = svc.domain_allocate_proxy("http")
    assert "allocated" in result

def test_rate_limiter_check():
    svc = RateLimiterService()
    result = svc.domain_check_rate("example.com", 100, 10.0, 20.0)
    assert result["site"] == "example.com"
    assert "passed" in result

def test_error_retry_calc():
    svc = ErrorRetryService()
    result = svc.domain_retry_calc("timeout", 2, 1.0)
    assert result["error_type"] == "timeout"
    assert result["attempt"] == 2
    assert result["delay_seconds"] > 0

def test_error_logger_log():
    svc = ErrorLoggerService()
    result = svc.domain_log_error("ERR-001", "Test error", "crawler", severity="warn")
    assert result["错误码"] == "ERR-001"
    assert result["错误信息"] == "Test error"

def test_cookie_mgr_get():
    svc = CookieMgrService()
    result = svc.domain_get_cookies("cookie_mgr")
    assert result["site"] == "cookie_mgr"
    assert isinstance(result["found"], bool)

def test_source_auth_auth():
    svc = SourceAuthService()
    result = svc.domain_authenticate("test-site.com", "token")
    assert result["authenticated"] is True
    assert result["site"] == "test-site.com"

def test_session_manager_create():
    svc = SessionManagerService()
    result = svc.domain_create_session("SESS-1", "config-a")
    assert result["会话标识"] == "SESS-1"
    assert result["status"] == "活跃"

def test_export_channel_export():
    svc = ExportChannelService()
    result = svc.domain_export("B-EXP-1", "csv", ["id", "name"])
    assert result["来源批次"] == "B-EXP-1"
    assert result["导出格式"] == "csv"

def test_crawl_audit_audit():
    svc = CrawlAuditService()
    result = svc.domain_audit("export", "batch-1", "admin")
    assert result["操作类型"] == "export"
    assert result["操作人"] == "admin"

def test_data_cleanup_cleanup():
    svc = DataCleanupService()
    result = svc.domain_cleanup("CLEAN-1", "result_store", 30)
    assert result["任务标识"] == "CLEAN-1"
    assert result["目标模块"] == "result_store"