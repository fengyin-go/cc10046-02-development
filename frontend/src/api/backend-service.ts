import { request } from './client'
import { moduleMeta } from '@/data/modules'
import type { ActionResult, EntryRow, OverviewResult, PageResult } from '@/data/types'

export { moduleMeta }

export async function listEntries(
  key: string,
  filters: Record<string, string> = {},
): Promise<PageResult> {
  const query = new URLSearchParams(filters).toString()
  const response = await request(`/api/${key}?${query}`)
  if (!response.ok) throw new Error('业务数据读取失败')
  return await response.json()
}

export async function createEntry(
  key: string,
  values: Record<string, string>,
): Promise<ActionResult> {
  const response = await request(`/api/${key}`, {
    method: 'POST',
    body: JSON.stringify({ values }),
  })
  return await response.json()
}

export async function runAction(
  key: string,
  id: number,
  action: string,
): Promise<ActionResult> {
  const response = await request(`/api/${key}/${id}/actions`, {
    method: 'POST',
    body: JSON.stringify({ action }),
  })
  return await response.json()
}

export async function downloadEntries(
  key: string,
  filters: Record<string, string> = {},
): Promise<void> {
  const query = new URLSearchParams(filters).toString()
  const response = await request(`/api/${key}/export?${query}`)
  if (!response.ok) throw new Error('业务数据导出失败')
  const url = URL.createObjectURL(await response.blob())
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `${key}.csv`
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(url)
}

export async function loadOverview(): Promise<OverviewResult> {
  const response = await request('/api/overview')
  if (!response.ok) throw new Error('运营概览读取失败')
  return await response.json()
}

export type CoverageSource = {
  source: string
  status: string
  sample_rows: number
  valid_rows: number
  missing_rows: number
  missing_values: number
  field_missing?: Record<string, number>
  coverage?: number | null
  coverage_percent?: number | null
  threshold: number
  threshold_percent: number
  passed: boolean
  result: string
  rounds: number
  last_mode?: string | null
  last_submitted_at?: string | null
}

export type CoverageBatchStatus = {
  batch_id: string
  required_sources: string[]
  key_fields: string[]
  threshold: number
  threshold_percent: number
  sources: CoverageSource[]
  deliverable: boolean
  delivery_status: string
  deliverable_sources: string[]
  readable_sources: string[]
  blocked_sources: string[]
  pending_sources: string[]
  shortfall_sources: string[]
  merged: {
    sample_rows: number
    valid_rows: number
    coverage_percent: number
    passed: boolean
  }
  conflict: boolean
  message: string
}

export type CoverageBatchSummary = {
  batch_id: string
  required_sources: string[]
  threshold_percent: number
  delivery_status: string
  deliverable: boolean
  readable_sources: string[]
  blocked_sources: string[]
  pending_sources: string[]
  merged_coverage_percent: number
  round_count: number
  opened_at?: string
}

export type CoverageRound = {
  id: number
  batch_id: string
  source: string
  round_no: number
  source_round_no: number
  mode: string
  submitted_at: string
  sample_rows: number
  valid_rows: number
  missing_rows: number
  missing_values: number
  coverage_percent: number
  threshold_percent: number
  result: string
  effective_sample_rows: number
  effective_valid_rows: number
  effective_missing_values: number
  effective_coverage_percent: number
  effective_result: string
  batch_deliverable: boolean
  delivery_status: string
  deliverable_scope: string[]
  readable_sources: string[]
  blocked_sources: string[]
  pending_sources: string[]
  merged_coverage_percent: number
  message: string
}

export type CoverageRoundsResult = {
  batch_id: string
  threshold_percent: number
  rounds: CoverageRound[]
  initial_threshold_records: CoverageRound[]
  current: CoverageBatchStatus
}

export async function listCoverageBatches(): Promise<CoverageBatchSummary[]> {
  const response = await request('/api/coverage/batches')
  if (!response.ok) throw new Error('覆盖率验收批次读取失败')
  return (await response.json()).items
}

export async function getCoverageBatch(batchId: string): Promise<CoverageBatchStatus> {
  const response = await request(`/api/coverage/batches/${encodeURIComponent(batchId)}`)
  if (!response.ok) throw new Error('覆盖率验收批次读取失败')
  return await response.json()
}

export async function getCoverageDeliverable(batchId: string): Promise<CoverageBatchStatus> {
  const response = await request(`/api/coverage/batches/${encodeURIComponent(batchId)}/deliverable`)
  if (!response.ok) throw new Error('可交付结果读取失败')
  return await response.json()
}

export async function getCoverageRounds(
  batchId: string,
  source?: string,
): Promise<CoverageRoundsResult> {
  const query = source ? `?${new URLSearchParams({ source })}` : ''
  const response = await request(`/api/coverage/batches/${encodeURIComponent(batchId)}/rounds${query}`)
  if (!response.ok) throw new Error('覆盖率验收历史读取失败')
  return await response.json()
}

export async function submitCoverageSource(
  batchId: string,
  payload: {
    source: string
    records: Record<string, unknown>[]
    mode?: 'append' | 'replace'
    key_fields?: string[]
    threshold?: number
  },
): Promise<{ ok: boolean; record: CoverageRound; batch: CoverageBatchStatus }> {
  const response = await request(`/api/coverage/batches/${encodeURIComponent(batchId)}/submit`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  const body = await response.json()
  if (!response.ok) throw new Error(body.detail ?? '来源样本提交失败')
  return body
}
