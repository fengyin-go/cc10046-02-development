"""覆盖率验收接口：映射采集记录、提交来源样本、核对交付范围和验收历史。

路由必须注册在通用资源路由之前：``/api/{module}/{entry_id}`` 会把
``/api/coverage/...`` 的下一段当成整数 entry_id 而返回 422。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.coverage_acceptance import coverage_service

router = APIRouter(prefix="/api/coverage", tags=["覆盖率验收"])


def _service():
    return coverage_service


@router.get("/batches")
def list_batches() -> dict[str, Any]:
    return {"items": _service().domain_batches()}


@router.post("/batches")
def open_batch(payload: dict[str, Any]) -> dict[str, Any]:
    try:
        batch = _service().domain_open_batch(
            payload.get("batch_id", ""),
            required_sources=payload.get("required_sources") or payload.get("sources"),
            threshold=payload.get("threshold"),
            key_fields=payload.get("key_fields"),
            mapping_rules=payload.get("mapping_rules"),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"ok": True, "batch": batch}


@router.get("/batches/{batch_id}")
def batch_status(batch_id: str) -> dict[str, Any]:
    snapshot = _service().domain_batch_status(batch_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"验收批次 {batch_id} 不存在")
    return snapshot


@router.get("/batches/{batch_id}/deliverable")
def batch_deliverable(batch_id: str) -> dict[str, Any]:
    result = _service().domain_deliverable(batch_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"验收批次 {batch_id} 不存在")
    return result


@router.get("/batches/{batch_id}/rounds")
def batch_rounds(batch_id: str, source: str | None = Query(default=None)) -> dict[str, Any]:
    result = _service().domain_rounds(batch_id, source)
    if result is None:
        raise HTTPException(status_code=404, detail=f"验收批次 {batch_id} 不存在")
    return result


@router.post("/batches/{batch_id}/submit")
def submit_source(batch_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        result = _service().domain_submit(
            batch_id,
            payload.get("source", ""),
            payload.get("records") or [],
            mode=payload.get("mode", "append"),
            mapping_rules=payload.get("mapping_rules"),
            key_fields=payload.get("key_fields"),
            threshold=payload.get("threshold"),
            submitted_at=payload.get("submitted_at"),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"ok": True, "record": result["record"], "batch": result["batch"]}


@router.post("/submit")
def submit_records(payload: dict[str, Any]) -> dict[str, Any]:
    """简化写法：批次和来源都放在请求体里提交一轮样本。"""
    return submit_source(payload.get("batch_id", ""), payload)


@router.get("/records")
def list_records(
    batch_id: str | None = Query(default=None),
    source: str | None = Query(default=None),
    result: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    items, total = _service().domain_records(
        batch_id=batch_id, source=source, result=result, page=page, size=size)
    return {"items": items, "total": total, "page": page, "size": size}


@router.post("/map")
def map_records(payload: dict[str, Any]) -> dict[str, Any]:
    return _service().domain_map_records(
        payload.get("records") or [],
        mapping_rules=payload.get("mapping_rules"),
        key_fields=payload.get("key_fields"),
        threshold=payload.get("threshold"),
    )


@router.post("/compute")
def compute_coverage(payload: dict[str, Any]) -> dict[str, Any]:
    return _service().domain_compute_coverage(
        payload.get("records") or [],
        key_fields=payload.get("key_fields"),
        threshold=payload.get("threshold"),
        mapping_rules=payload.get("mapping_rules"),
    )
