"""覆盖率验收领域服务：用映射后的采集记录按来源核对关键字段覆盖率。

业务口径：

* 一条采集行只有在关键字段“实际采到”时才算有效行。价格为 ``0`` 的实采行
  是有效行；映射时用默认值补出来的 ``0`` 不算有效，并计入缺值。
* 同一来源可以分多次提交。追加提交按“全部来源行 + 原始有效行”累加；
  重新提交（replace）表示修订该来源的样本，会整体替换本来源之前的累计值。
* 阈值按来源分别判断。合并覆盖率只作为参考，不能把未达标来源“合并”成
  可交付；只要还有一个必需来源未达标或未提交，批次就不可交付。
* 每轮提交都会留下不可变的验收记录（含当时的阈值、结果和完整交付范围），
  因此重新提交后仍能追溯最初的阈值记录。
"""
from __future__ import annotations

import time
from typing import Any

from app.store import store

BATCH_TABLE = "_coverage_batches"
SUBMISSION_TABLE = "_coverage_submissions"

MODE_APPEND = "append"
MODE_REPLACE = "replace"
VALID_MODES = {MODE_APPEND, MODE_REPLACE}

DEFAULT_KEY_FIELDS = ["price"]
DEFAULT_THRESHOLD = 0.9
DEFAULT_MAPPING_RULES = [
    {"source": "price", "target": "price", "default": "0", "transform": "int"},
]

_MISSING = object()


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def normalize_threshold(value: Any) -> float:
    """把阈值统一成 0~1 的比例，兼容 ``90`` 和 ``0.9`` 两种写法。"""
    if value is None:
        return DEFAULT_THRESHOLD
    try:
        number = float(value)
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD
    if number > 1:
        number = number / 100.0
    return max(0.0, min(number, 1.0))


def _threshold_percent(value: Any) -> float:
    return round(normalize_threshold(value) * 100, 2)


def _row_id(rows: list[dict[str, Any]]) -> int:
    return max((int(row.get("id", 0)) for row in rows), default=0) + 1


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


def map_record(
    record: dict[str, Any],
    mapping_rules: list[dict[str, Any]],
) -> tuple[dict[str, Any], set[str]]:
    """按映射规则转换一行数据，并记录哪些目标字段是默认值补出来的。

    返回值第二项是“默认补出”的目标字段集合。调用方据此判断有效行：
    实采到的 ``0`` 不在集合里，默认补出的 ``0`` 在集合里。
    """
    mapped: dict[str, Any] = {}
    defaulted: set[str] = set()
    for rule in mapping_rules:
        source_field = str(rule.get("source", ""))
        target_field = str(rule.get("target", ""))
        if not target_field:
            continue
        default = rule.get("default", "")
        transform = rule.get("transform", "")

        raw = record.get(source_field, _MISSING)
        if raw is _MISSING or _is_blank(raw):
            value = default
            defaulted.add(target_field)
        else:
            value = raw
        # 默认值和实采值走同一套转换，保证 mapped 里的 0 类型一致；
        # 是否算“有效行”仍由 defaulted 标记决定。
        if transform == "upper":
            value = str(value).upper()
        elif transform == "lower":
            value = str(value).lower()
        elif transform == "int":
            try:
                value = int(float(value))
            except (TypeError, ValueError):
                # 采到了但无法转成整数，等价于没有采到有效值。
                value = 0
                defaulted.add(target_field)
        mapped[target_field] = value
    return mapped, defaulted


def _prepare_record(
    record: dict[str, Any],
    mapping_rules: list[dict[str, Any]] | None,
) -> tuple[dict[str, Any], set[str]]:
    """把原始记录或带来源标记的映射记录整理成 ``(映射值, 默认字段)``。

    记录里带 ``_defaulted_fields`` / ``_collected_fields`` 标记时，说明它已经
    映射过并且自带来源归属，直接按标记判断，不再重复套用映射规则；否则
    ``mapping_rules`` 为空表示记录本身就是映射后的结构，所有非空字段视为实采。
    """
    if "_defaulted_fields" in record or "_collected_fields" in record:
        mapped = {
            key: value for key, value in record.items() if not str(key).startswith("_")
        }
        defaulted = {
            str(field) for field in (record.get("_defaulted_fields") or [])
        }
        collected = record.get("_collected_fields")
        if collected is not None:
            defaulted |= set(mapped) - {str(field) for field in collected}
        return mapped, defaulted

    if not mapping_rules:
        return dict(record), set()

    return map_record(record, mapping_rules)


def summarize_rows(
    prepared_rows: list[tuple[dict[str, Any], set[str]]],
    key_fields: list[str],
    threshold: Any = DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    """统计一组映射行的关键字段覆盖情况。

    ``missing_rows`` 是至少缺一个关键字段的行数；``missing_values`` 是缺失的
    关键字段格数。审查员看的是缺值实际数量，因此两者在任何阈值结果下都会返回。
    """
    key_fields = [str(field) for field in key_fields] or list(DEFAULT_KEY_FIELDS)
    threshold_ratio = normalize_threshold(threshold)

    sample_rows = len(prepared_rows)
    valid_rows = 0
    missing_rows = 0
    missing_values = 0
    field_missing = {field: 0 for field in key_fields}

    for mapped, defaulted in prepared_rows:
        row_missing = [
            field for field in key_fields
            if field not in mapped or _is_blank(mapped[field]) or field in defaulted
        ]
        if row_missing:
            missing_rows += 1
            missing_values += len(row_missing)
            for field in row_missing:
                field_missing[field] += 1
        else:
            valid_rows += 1

    coverage = valid_rows / sample_rows if sample_rows else 0.0
    passed = sample_rows > 0 and coverage + 1e-12 >= threshold_ratio
    return {
        "sample_rows": sample_rows,
        "valid_rows": valid_rows,
        "missing_rows": missing_rows,
        "missing_values": missing_values,
        "field_missing": field_missing,
        "coverage": round(coverage, 6),
        "coverage_percent": round(coverage * 100, 2),
        "threshold": threshold_ratio,
        "threshold_percent": _threshold_percent(threshold_ratio),
        "passed": passed,
        "result": "通过" if passed else "未通过",
    }


def _sum_metrics(metrics_list: list[dict[str, Any]]) -> dict[str, Any]:
    total = {
        "sample_rows": 0,
        "valid_rows": 0,
        "missing_rows": 0,
        "missing_values": 0,
        "field_missing": {},
    }
    for metrics in metrics_list:
        total["sample_rows"] += metrics.get("sample_rows", 0)
        total["valid_rows"] += metrics.get("valid_rows", 0)
        total["missing_rows"] += metrics.get("missing_rows", 0)
        total["missing_values"] += metrics.get("missing_values", 0)
        for field, count in (metrics.get("field_missing") or {}).items():
            total["field_missing"][field] = total["field_missing"].get(field, 0) + count
    return total


def _metrics_with_ratio(metrics: dict[str, Any], threshold: float) -> dict[str, Any]:
    sample = metrics.get("sample_rows", 0)
    valid = metrics.get("valid_rows", 0)
    coverage = valid / sample if sample else 0.0
    passed = sample > 0 and coverage + 1e-12 >= threshold
    return {
        **metrics,
        "coverage": round(coverage, 6),
        "coverage_percent": round(coverage * 100, 2),
        "threshold": threshold,
        "threshold_percent": round(threshold * 100, 2),
        "passed": passed,
        "result": "通过" if passed else "未通过",
    }


class CoverageAcceptanceService:
    """覆盖率验收：批次定义、来源提交、阈值判定和交付范围快照。"""

    def __init__(self, seed_demo: bool = True) -> None:
        if seed_demo:
            self.ensure_demo()

    # ------------------------------------------------------------------
    # 数据表
    # ------------------------------------------------------------------
    def _batch_rows(self) -> list[dict[str, Any]]:
        return store.rows(BATCH_TABLE)

    def _submission_rows(self) -> list[dict[str, Any]]:
        return store.rows(SUBMISSION_TABLE)

    def _find_batch(self, batch_id: str) -> dict[str, Any] | None:
        for batch in self._batch_rows():
            if batch.get("batch_id") == batch_id:
                return batch
        return None

    def _batch_submissions(self, batch_id: str) -> list[dict[str, Any]]:
        return [
            row for row in self._submission_rows()
            if row.get("batch_id") == batch_id
        ]

    # ------------------------------------------------------------------
    # 覆盖率计算入口
    # ------------------------------------------------------------------
    def domain_map_records(
        self,
        records: list[dict[str, Any]],
        mapping_rules: list[dict[str, Any]] | None = None,
        key_fields: list[str] | None = None,
        threshold: Any = DEFAULT_THRESHOLD,
    ) -> dict[str, Any]:
        """映射一批采集记录并计算关键字段覆盖率（不落库的预览入口）。"""
        keys = [str(field) for field in (key_fields or DEFAULT_KEY_FIELDS)]
        rules = DEFAULT_MAPPING_RULES if mapping_rules is None else mapping_rules
        prepared = [_prepare_record(record, rules) for record in records]
        items: list[dict[str, Any]] = []
        for mapped, defaulted in prepared:
            row_missing = [
                field for field in keys
                if field not in mapped or _is_blank(mapped[field]) or field in defaulted
            ]
            items.append({
                "mapped": mapped,
                "defaulted_fields": sorted(defaulted),
                "collected_fields": sorted(set(mapped) - defaulted),
                "valid": not row_missing,
                "missing_fields": row_missing,
            })
        summary = summarize_rows(prepared, keys, threshold)
        return {"items": items, "summary": summary, "key_fields": keys}

    def domain_compute_coverage(
        self,
        records: list[dict[str, Any]],
        key_fields: list[str] | None = None,
        threshold: Any = DEFAULT_THRESHOLD,
        mapping_rules: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """只算覆盖率，不保留逐行明细。"""
        return self.domain_map_records(
            records, mapping_rules=mapping_rules,
            key_fields=key_fields, threshold=threshold,
        )["summary"]

    # ------------------------------------------------------------------
    # 批次和提交
    # ------------------------------------------------------------------
    def domain_open_batch(
        self,
        batch_id: str,
        required_sources: list[str] | None = None,
        threshold: Any = DEFAULT_THRESHOLD,
        key_fields: list[str] | None = None,
        mapping_rules: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """登记一个验收批次，声明交付所需来源与统一阈值。"""
        batch_id = str(batch_id or "").strip()
        if not batch_id:
            raise ValueError("批次标识不能为空")
        existing = self._find_batch(batch_id)
        if existing is not None:
            return existing
        sources = [str(item).strip() for item in (required_sources or []) if str(item).strip()]
        batch = {
            "id": _row_id(self._batch_rows()),
            "batch_id": batch_id,
            "required_sources": list(dict.fromkeys(sources)),
            "threshold": normalize_threshold(threshold),
            "key_fields": [str(field) for field in (key_fields or DEFAULT_KEY_FIELDS)],
            "mapping_rules": list(
                DEFAULT_MAPPING_RULES if mapping_rules is None else mapping_rules
            ),
            "opened_at": _now(),
            "status": "验收中",
        }
        self._batch_rows().append(batch)
        return batch

    def _get_or_create_batch(
        self,
        batch_id: str,
        mapping_rules: list[dict[str, Any]] | None,
        key_fields: list[str] | None,
        threshold: Any,
    ) -> dict[str, Any]:
        batch = self._find_batch(batch_id)
        if batch is not None:
            return batch
        return self.domain_open_batch(
            batch_id,
            required_sources=[],
            threshold=threshold,
            key_fields=key_fields,
            mapping_rules=mapping_rules,
        )

    def domain_submit(
        self,
        batch_id: str,
        source: str,
        records: list[dict[str, Any]],
        *,
        mode: str = MODE_APPEND,
        mapping_rules: list[dict[str, Any]] | None = None,
        key_fields: list[str] | None = None,
        threshold: Any = None,
        submitted_at: str | None = None,
    ) -> dict[str, Any]:
        """提交一个来源的采集记录，生成一条不可变的覆盖率验收记录。

        ``mode="append"`` 用于分片提交，样本量和有效行数与之前的提交累加；
        ``mode="replace"`` 用于重新提交，整体替换本来源的累计样本。
        """
        batch_id = str(batch_id or "").strip()
        source = str(source or "").strip()
        if not batch_id:
            raise ValueError("批次标识不能为空")
        if not source:
            raise ValueError("来源不能为空")
        if mode not in VALID_MODES:
            raise ValueError(f"提交方式只支持 append / replace，收到：{mode}")
        if not isinstance(records, list):
            raise ValueError("records 必须是采集记录数组")

        if mapping_rules is None:
            batch = self._get_or_create_batch(batch_id, None, key_fields, threshold)
            rules = list(batch.get("mapping_rules") or [])
        else:
            batch = self._get_or_create_batch(batch_id, mapping_rules, key_fields, threshold)
            rules = list(mapping_rules)
        keys = [
            str(field)
            for field in (key_fields or batch.get("key_fields") or DEFAULT_KEY_FIELDS)
        ]
        threshold_ratio = normalize_threshold(
            batch.get("threshold") if threshold is None else threshold
        )

        if source not in batch["required_sources"]:
            batch["required_sources"].append(source)

        prepared = [_prepare_record(record, rules) for record in records]
        current = summarize_rows(prepared, keys, threshold_ratio)

        previous = self._latest_source_round(batch_id, source)
        if mode == MODE_REPLACE or previous is None:
            effective = {
                "sample_rows": current["sample_rows"],
                "valid_rows": current["valid_rows"],
                "missing_rows": current["missing_rows"],
                "missing_values": current["missing_values"],
                "field_missing": dict(current["field_missing"]),
            }
        else:
            previous_effective = {
                "sample_rows": previous.get("effective_sample_rows", 0),
                "valid_rows": previous.get("effective_valid_rows", 0),
                "missing_rows": previous.get("effective_missing_rows", 0),
                "missing_values": previous.get("effective_missing_values", 0),
                "field_missing": dict(previous.get("effective_field_missing") or {}),
            }
            effective = _sum_metrics([previous_effective, current])

        effective = _metrics_with_ratio(effective, threshold_ratio)
        source_round_no = sum(
            1 for row in self._batch_submissions(batch_id)
            if row.get("source") == source
        ) + 1
        global_round_no = len(self._batch_submissions(batch_id)) + 1
        record = {
            "id": _row_id(self._submission_rows()),
            "batch_id": batch_id,
            "source": source,
            "round_no": global_round_no,
            "source_round_no": source_round_no,
            "mode": mode,
            "submitted_at": submitted_at or _now(),
            "key_fields": keys,
            "sample_rows": current["sample_rows"],
            "valid_rows": current["valid_rows"],
            "missing_rows": current["missing_rows"],
            "missing_values": current["missing_values"],
            "field_missing": dict(current["field_missing"]),
            "coverage": current["coverage"],
            "coverage_percent": current["coverage_percent"],
            "threshold": threshold_ratio,
            "threshold_percent": round(threshold_ratio * 100, 2),
            "passed": current["passed"],
            "result": current["result"],
            # 本来源累计口径（追加累加 / 重新提交替换）
            "effective_sample_rows": effective["sample_rows"],
            "effective_valid_rows": effective["valid_rows"],
            "effective_missing_rows": effective["missing_rows"],
            "effective_missing_values": effective["missing_values"],
            "effective_field_missing": dict(effective["field_missing"]),
            "effective_coverage": effective["coverage"],
            "effective_coverage_percent": effective["coverage_percent"],
            "effective_passed": effective["passed"],
            "effective_result": effective["result"],
        }

        snapshot = self._build_snapshot(batch, extra=record)
        record.update({
            "batch_deliverable": snapshot["deliverable"],
            "delivery_status": snapshot["delivery_status"],
            "deliverable_scope": snapshot["deliverable_sources"],
            "readable_sources": snapshot["readable_sources"],
            "blocked_sources": snapshot["blocked_sources"],
            "pending_sources": snapshot["pending_sources"],
            "missing_sources": snapshot["missing_sources"],
            "merged_coverage": snapshot["merged"]["coverage"],
            "merged_coverage_percent": snapshot["merged"]["coverage_percent"],
            "merged_passed": snapshot["merged"]["passed"],
            "conflict": snapshot["conflict"],
            "message": snapshot["message"],
        })
        self._submission_rows().append(record)
        batch["status"] = snapshot["delivery_status"]

        return {
            "record": record,
            "batch": snapshot,
            "summary": current,
        }

    def _latest_source_round(self, batch_id: str, source: str) -> dict[str, Any] | None:
        """取该来源的最后一次提交（按提交顺序，不受补录时间戳影响）。"""
        candidates = [
            row for row in self._batch_submissions(batch_id)
            if row.get("source") == source
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda row: int(row.get("round_no", 0)))

    # ------------------------------------------------------------------
    # 批次快照 / 可交付查询
    # ------------------------------------------------------------------
    def _build_snapshot(
        self,
        batch: dict[str, Any],
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """基于各来源当前累计验收结果生成批次交付快照。"""
        batch_id = batch["batch_id"]
        latest: dict[str, dict[str, Any]] = {}
        for row in self._batch_submissions(batch_id):
            previous = latest.get(str(row.get("source")))
            if previous is None or int(row.get("round_no", 0)) > int(previous.get("round_no", 0)):
                latest[str(row.get("source"))] = row
        if extra is not None:
            latest[str(extra["source"])] = extra

        required = list(batch.get("required_sources") or [])
        for source in latest:
            if source not in required:
                required.append(source)

        threshold = normalize_threshold(batch.get("threshold"))
        sources: list[dict[str, Any]] = []
        readable: list[str] = []
        blocked: list[str] = []
        pending: list[str] = []

        for source in required:
            row = latest.get(source)
            if row is None:
                pending.append(source)
                sources.append({
                    "source": source,
                    "status": "待提交",
                    "sample_rows": 0,
                    "valid_rows": 0,
                    "missing_rows": 0,
                    "missing_values": 0,
                    "coverage": None,
                    "coverage_percent": None,
                    "threshold": threshold,
                    "threshold_percent": round(threshold * 100, 2),
                    "passed": False,
                    "result": "待提交",
                    "rounds": 0,
                    "last_mode": None,
                })
                continue

            passed = bool(row.get("effective_passed"))
            if passed:
                readable.append(source)
            else:
                blocked.append(source)
            sources.append({
                "source": source,
                "status": "已通过" if passed else "未通过",
                "sample_rows": row.get("effective_sample_rows", 0),
                "valid_rows": row.get("effective_valid_rows", 0),
                "missing_rows": row.get("effective_missing_rows", 0),
                "missing_values": row.get("effective_missing_values", 0),
                "field_missing": dict(row.get("effective_field_missing") or {}),
                "coverage": row.get("effective_coverage"),
                "coverage_percent": row.get("effective_coverage_percent"),
                "threshold": row.get("threshold", threshold),
                "threshold_percent": row.get("threshold_percent", round(threshold * 100, 2)),
                "passed": passed,
                "result": "通过" if passed else "未通过",
                "rounds": sum(
                    1 for item in self._batch_submissions(batch_id)
                    if item.get("source") == source
                ) + (1 if extra is not None and extra.get("source") == source else 0),
                "last_mode": row.get("mode"),
                "last_submitted_at": row.get("submitted_at"),
            })

        submitted_metrics = [
            {
                "sample_rows": row.get("effective_sample_rows", 0),
                "valid_rows": row.get("effective_valid_rows", 0),
                "missing_rows": row.get("effective_missing_rows", 0),
                "missing_values": row.get("effective_missing_values", 0),
                "field_missing": dict(row.get("effective_field_missing") or {}),
            }
            for row in latest.values()
        ]
        merged = _metrics_with_ratio(_sum_metrics(submitted_metrics), threshold)
        merged["applies_to_delivery"] = False
        merged["note"] = "合并覆盖率仅作参考，交付按每个来源的阈值分别判定"

        deliverable = bool(required) and not blocked and not pending
        shortfall = blocked + pending
        conflict = bool(merged["passed"]) and not deliverable
        if deliverable:
            delivery_status = "可交付"
            message = (
                f"批次 {batch_id} 已可交付，交付范围：{'、'.join(required)}；"
                f"合并覆盖 {merged['valid_rows']}/{merged['sample_rows']}"
                f"（{merged['coverage_percent']}%）。"
            )
        elif pending and blocked:
            delivery_status = "不可交付"
            message = (
                f"批次 {batch_id} 暂不可交付：{'、'.join(pending)} 尚未提交，"
                f"{'、'.join(blocked)} 未达标；当前可读已确认来源："
                f"{'、'.join(readable) or '无'}。"
            )
        elif pending:
            delivery_status = "待验收"
            message = (
                f"批次 {batch_id} 还差 {'、'.join(pending)} 提交验收；"
                f"当前可读已确认来源：{'、'.join(readable) or '无'}。"
            )
        else:
            delivery_status = "不可交付"
            message = (
                f"批次 {batch_id} 暂不可交付：{'、'.join(blocked)} 未达到 "
                f"{round(threshold * 100, 2)}% 阈值；当前可读已确认来源："
                f"{'、'.join(readable) or '无'}。"
            )
        if conflict:
            message += (
                f" 注意：合并覆盖 {merged['valid_rows']}/{merged['sample_rows']}"
                f"（{merged['coverage_percent']}%）虽达标，但分来源验收存在冲突，"
                "不能据此交付。"
            )

        return {
            "batch_id": batch_id,
            "required_sources": required,
            "key_fields": list(batch.get("key_fields") or DEFAULT_KEY_FIELDS),
            "threshold": threshold,
            "threshold_percent": round(threshold * 100, 2),
            "sources": sources,
            "deliverable": deliverable,
            "delivery_status": delivery_status,
            "deliverable_sources": list(required) if deliverable else [],
            "readable_sources": readable,
            "blocked_sources": blocked,
            "pending_sources": pending,
            "missing_sources": pending,
            "shortfall_sources": shortfall,
            "merged": merged,
            "conflict": conflict,
            "conflict_detail": (
                "合并覆盖率达标但存在未达标来源，分来源阈值优先，批次不可交付"
                if conflict else None
            ),
            "message": message,
        }

    def domain_batch_status(self, batch_id: str) -> dict[str, Any] | None:
        """查询批次当前的可交付结果和各来源有效行数。"""
        batch = self._find_batch(batch_id)
        if batch is None:
            return None
        snapshot = self._build_snapshot(batch)
        snapshot["opened_at"] = batch.get("opened_at")
        snapshot["mapping_rules"] = batch.get("mapping_rules")
        snapshot["round_count"] = len(self._batch_submissions(batch_id))
        return snapshot

    def domain_deliverable(self, batch_id: str) -> dict[str, Any] | None:
        """结果存储的交付闸门：只有全部分来源达标才返回交付范围。"""
        snapshot = self.domain_batch_status(batch_id)
        if snapshot is None:
            return None
        return {
            "batch_id": batch_id,
            "deliverable": snapshot["deliverable"],
            "delivery_status": snapshot["delivery_status"],
            "deliverable_sources": snapshot["deliverable_sources"],
            "readable_sources": snapshot["readable_sources"],
            "blocked_sources": snapshot["blocked_sources"],
            "pending_sources": snapshot["pending_sources"],
            "sources": snapshot["sources"],
            "merged": snapshot["merged"],
            "conflict": snapshot["conflict"],
            "message": snapshot["message"],
        }

    def domain_batches(self) -> list[dict[str, Any]]:
        """所有验收批次及其当前状态，供工作台选择批次。"""
        result = []
        for batch in self._batch_rows():
            snapshot = self.domain_batch_status(batch["batch_id"])
            if snapshot is None:
                continue
            result.append({
                "batch_id": batch["batch_id"],
                "required_sources": snapshot["required_sources"],
                "threshold_percent": snapshot["threshold_percent"],
                "delivery_status": snapshot["delivery_status"],
                "deliverable": snapshot["deliverable"],
                "readable_sources": snapshot["readable_sources"],
                "blocked_sources": snapshot["blocked_sources"],
                "pending_sources": snapshot["pending_sources"],
                "merged_coverage_percent": snapshot["merged"]["coverage_percent"],
                "round_count": snapshot["round_count"],
                "opened_at": batch.get("opened_at"),
            })
        return result

    # ------------------------------------------------------------------
    # 历史轮次
    # ------------------------------------------------------------------
    def domain_rounds(
        self,
        batch_id: str,
        source: str | None = None,
    ) -> dict[str, Any] | None:
        """完整验收历史：每轮的阈值、结果、累计值和当时的交付范围。"""
        batch = self._find_batch(batch_id)
        if batch is None:
            return None
        rounds = [
            dict(row) for row in self._batch_submissions(batch_id)
            if source is None or row.get("source") == source
        ]
        # 按实际提交顺序排列：补录的 submitted_at 可以更早，但轮次不会倒退。
        rounds.sort(key=lambda row: int(row.get("round_no", 0)))

        # 每个来源最初的阈值记录：后续重新提交不会覆盖它。
        first_by_source: dict[str, dict[str, Any]] = {}
        for row in rounds:
            first_by_source.setdefault(str(row.get("source")), row)

        current = self.domain_batch_status(batch_id)
        return {
            "batch_id": batch_id,
            "source": source,
            "threshold_percent": round(normalize_threshold(batch.get("threshold")) * 100, 2),
            "rounds": rounds,
            "initial_threshold_records": list(first_by_source.values()),
            "current": current,
        }

    def domain_records(
        self,
        batch_id: str | None = None,
        source: str | None = None,
        result: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """覆盖率验收数据列表：一行对应一次来源提交。"""
        rows = [
            dict(row) for row in self._submission_rows()
            if (batch_id is None or row.get("batch_id") == batch_id)
            and (source is None or row.get("source") == source)
            and (result is None or row.get("result") == result)
        ]
        rows.sort(key=lambda row: (row.get("batch_id") or "", int(row.get("round_no", 0))))
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    # ------------------------------------------------------------------
    # 演示数据
    # ------------------------------------------------------------------
    def ensure_demo(self) -> None:
        """准备一条冲突演示批次：主站 95/100 达标，镜像站 1/5 未达标。"""
        if self._batch_rows():
            return
        demo_batch = "BATCH-PRICE-2026-11-24"
        self.domain_open_batch(
            demo_batch,
            required_sources=["主站", "镜像站"],
            threshold=0.9,
            key_fields=["price"],
            mapping_rules=[],
        )
        main_rows = [
            {"price": 0 if index % 10 == 0 else 10 + index % 40}
            for index in range(95)
        ] + [
            {"price": 0, "_defaulted_fields": ["price"]}
            for _ in range(5)
        ]
        mirror_rows = [{"price": 20}] + [
            {"price": 0, "_defaulted_fields": ["price"]}
            for _ in range(4)
        ]
        self.domain_submit(
            demo_batch, "主站", main_rows,
            mode=MODE_APPEND, mapping_rules=[],
            submitted_at="2026-11-24 09:00:00",
        )
        self.domain_submit(
            demo_batch, "镜像站", mirror_rows,
            mode=MODE_APPEND, mapping_rules=[],
            submitted_at="2026-11-24 09:05:00",
        )


coverage_service = CoverageAcceptanceService()
