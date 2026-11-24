"""覆盖率验收：默认值口径、分来源阈值、追加累计和重新提交历史。"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.services.coverage_acceptance import (
    CoverageAcceptanceService,
    coverage_service,
    map_record,
    summarize_rows,
)


def fresh_batch(service: CoverageAcceptanceService, batch_id: str, sources: list[str]) -> str:
    service.domain_open_batch(
        batch_id,
        required_sources=sources,
        threshold=90,
        key_fields=["price"],
        mapping_rules=[],
    )
    return batch_id


class TestDefaultZero:
    def test_collected_zero_is_valid(self):
        mapped, defaulted = map_record(
            {"price": "0"},
            [{"source": "price", "target": "price", "default": "0", "transform": "int"}],
        )
        assert mapped == {"price": 0}
        assert defaulted == set()

    def test_default_zero_is_not_valid(self):
        mapped, defaulted = map_record(
            {},
            [{"source": "price", "target": "price", "default": "0", "transform": "int"}],
        )
        assert mapped == {"price": 0}
        assert defaulted == {"price"}

    def test_blank_source_uses_default(self):
        _, defaulted = map_record(
            {"price": ""},
            [{"source": "price", "target": "price", "default": "0", "transform": "int"}],
        )
        assert defaulted == {"price"}

    def test_threshold_accepts_percent_and_ratio(self):
        assert summarize_rows([], ["price"], 90)["threshold"] == pytest.approx(0.9)
        assert summarize_rows([], ["price"], 0.9)["threshold"] == pytest.approx(0.9)


class TestSourceThresholds:
    def test_merged_pass_does_not_override_blocked_source(self, ):
        service = CoverageAcceptanceService(seed_demo=False)
        batch_id = fresh_batch(service, "T-CONFLICT", ["主站", "镜像站"])
        service.domain_submit(
            batch_id, "主站",
            [{"price": 10} for _ in range(95)]
            + [{"price": 0, "_defaulted_fields": ["price"]} for _ in range(5)],
            mapping_rules=[],
        )
        result = service.domain_submit(
            batch_id, "镜像站",
            [{"price": 20}]
            + [{"price": 0, "_defaulted_fields": ["price"]} for _ in range(4)],
            mapping_rules=[],
        )
        snapshot = result["batch"]
        assert snapshot["merged"]["valid_rows"] == 96
        assert snapshot["merged"]["sample_rows"] == 105
        assert snapshot["merged"]["passed"] is True
        assert snapshot["deliverable"] is False
        assert snapshot["blocked_sources"] == ["镜像站"]
        assert snapshot["readable_sources"] == ["主站"]
        assert snapshot["conflict"] is True

        mirror = next(item for item in snapshot["sources"] if item["source"] == "镜像站")
        assert (mirror["sample_rows"], mirror["valid_rows"]) == (5, 1)
        assert mirror["missing_values"] == 4

    def test_resubmit_makes_batch_deliverable_and_keeps_history(self):
        service = CoverageAcceptanceService(seed_demo=False)
        batch_id = fresh_batch(service, "T-RESUBMIT", ["主站", "镜像站"])
        service.domain_submit(
            batch_id, "主站",
            [{"price": 10} for _ in range(95)]
            + [{"price": 0, "_defaulted_fields": ["price"]} for _ in range(5)],
            mapping_rules=[],
        )
        first = service.domain_submit(
            batch_id, "镜像站",
            [{"price": 20}]
            + [{"price": 0, "_defaulted_fields": ["price"]} for _ in range(4)],
            mapping_rules=[],
        )
        assert first["batch"]["deliverable"] is False

        second = service.domain_submit(
            batch_id, "镜像站",
            [{"price": 20 + index} for index in range(5)],
            mode="replace",
            mapping_rules=[],
        )
        snapshot = second["batch"]
        assert snapshot["deliverable"] is True
        assert snapshot["deliverable_sources"] == ["主站", "镜像站"]
        assert snapshot["blocked_sources"] == []
        assert snapshot["merged"]["valid_rows"] == 100
        assert snapshot["merged"]["sample_rows"] == 105

        history = service.domain_rounds(batch_id, "镜像站")
        assert [row["source_round_no"] for row in history["rounds"]] == [1, 2]
        assert [row["mode"] for row in history["rounds"]] == ["append", "replace"]
        first_round = history["initial_threshold_records"][0]
        assert first_round["source_round_no"] == 1
        assert first_round["result"] == "未通过"
        assert first_round["threshold_percent"] == 90.0
        assert first_round["deliverable_scope"] == []
        assert history["rounds"][0]["deliverable_scope"] == []
        assert history["rounds"][1]["deliverable_scope"] == ["主站", "镜像站"]
        assert history["rounds"][1]["batch_deliverable"] is True

    def test_append_accumulates_sample_and_valid_rows(self):
        service = CoverageAcceptanceService(seed_demo=False)
        batch_id = fresh_batch(service, "T-APPEND", ["主站"])
        service.domain_submit(
            batch_id, "主站", [{"price": 1} for _ in range(9)],
            mapping_rules=[],
        )
        result = service.domain_submit(
            batch_id, "主站",
            [{"price": 2}, {"price": 0, "_defaulted_fields": ["price"]}],
            mapping_rules=[],
        )
        record = result["record"]
        assert record["sample_rows"] == 2
        assert record["valid_rows"] == 1
        assert record["effective_sample_rows"] == 11
        assert record["effective_valid_rows"] == 10
        assert record["effective_coverage_percent"] == pytest.approx(90.91)
        assert record["effective_result"] == "通过"

    def test_pending_source_keeps_batch_undeliverable(self):
        service = CoverageAcceptanceService(seed_demo=False)
        batch_id = fresh_batch(service, "T-PENDING", ["主站", "镜像站"])
        result = service.domain_submit(
            batch_id, "主站", [{"price": 1} for _ in range(10)],
            mapping_rules=[],
        )
        snapshot = result["batch"]
        assert snapshot["deliverable"] is False
        assert snapshot["delivery_status"] == "待验收"
        assert snapshot["pending_sources"] == ["镜像站"]
        assert snapshot["readable_sources"] == ["主站"]
        assert snapshot["message"]

    def test_missing_values_reported_even_when_passed(self):
        service = CoverageAcceptanceService(seed_demo=False)
        batch_id = fresh_batch(service, "T-MISSING", ["主站"])
        result = service.domain_submit(
            batch_id, "主站",
            [{"price": 1} for _ in range(95)]
            + [{"price": 0, "_defaulted_fields": ["price"]} for _ in range(5)],
            mapping_rules=[],
        )
        record = result["record"]
        assert record["effective_passed"] is True
        assert record["effective_missing_rows"] == 5
        assert record["effective_missing_values"] == 5

    def test_backdated_append_stays_latest_round(self):
        service = CoverageAcceptanceService(seed_demo=False)
        batch_id = fresh_batch(service, "T-BACKDATED", ["主站"])
        service.domain_submit(
            batch_id, "主站", [{"price": 1} for _ in range(10)],
            mapping_rules=[], submitted_at="2026-11-24 20:00:00",
        )
        result = service.domain_submit(
            batch_id, "主站", [{"price": 2} for _ in range(2)],
            mapping_rules=[], submitted_at="2026-11-24 01:00:00",
        )
        assert result["record"]["source_round_no"] == 2
        assert result["record"]["effective_sample_rows"] == 12
        source = result["batch"]["sources"][0]
        assert source["sample_rows"] == 12
        history = service.domain_rounds(batch_id)
        assert [row["source_round_no"] for row in history["rounds"]] == [1, 2]


class TestDemoSeed:
    def test_demo_batch(self):
        service = CoverageAcceptanceService(seed_demo=False)
        service.ensure_demo()
        snapshot = service.domain_batch_status("BATCH-PRICE-2026-11-24")
        assert snapshot["merged"]["valid_rows"] == 96
        assert snapshot["merged"]["sample_rows"] == 105
        assert snapshot["deliverable"] is False
        assert snapshot["conflict"] is True


def test_shared_service_is_initialized():
    assert coverage_service.domain_batches()
