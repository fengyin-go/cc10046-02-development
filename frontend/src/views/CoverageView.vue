<template>
  <section class="page coverage-page" data-testid="coverage-page">
    <header class="page-head">
      <div>
        <h2>覆盖率验收</h2>
        <p class="page-desc">
          用映射后的采集记录按来源核对关键字段覆盖率；只有各来源分别达到阈值，采集批次才可交付。
        </p>
      </div>
      <div class="page-actions">
        <label class="batch-picker">
          <span>验收批次</span>
          <select v-model="activeBatchId" data-testid="batch-select" @change="loadBatch">
            <option v-for="batch in batches" :key="batch.batch_id" :value="batch.batch_id">
              {{ batch.batch_id }}（{{ batch.delivery_status }}）
            </option>
          </select>
        </label>
        <button class="btn" data-testid="refresh" type="button" @click="reloadAll">刷新</button>
      </div>
    </header>

    <p v-if="errorMessage" class="error-text" data-testid="error-text">{{ errorMessage }}</p>

    <template v-if="status">
      <div class="stat-row">
        <article class="stat-card" data-testid="stat-deliverable">
          <span class="stat-label">交付结论</span>
          <strong class="stat-value" :class="status.deliverable ? 'ok' : 'bad'">
            {{ status.delivery_status }}
          </strong>
        </article>
        <article class="stat-card" data-testid="stat-threshold">
          <span class="stat-label">关键字段阈值</span>
          <strong class="stat-value">{{ status.threshold_percent }}%</strong>
        </article>
        <article class="stat-card" data-testid="stat-merged">
          <span class="stat-label">合并覆盖（仅参考）</span>
          <strong class="stat-value">
            {{ status.merged.valid_rows }}/{{ status.merged.sample_rows }}
            （{{ status.merged.coverage_percent }}%）
          </strong>
        </article>
        <article class="stat-card" data-testid="stat-scope">
          <span class="stat-label">现在可读的已确认来源</span>
          <strong class="stat-value">{{ status.readable_sources.join('、') || '无' }}</strong>
        </article>
      </div>

      <p
        class="delivery-banner"
        :class="status.deliverable ? 'ok' : 'bad'"
        data-testid="delivery-message"
      >
        {{ status.message }}
      </p>
      <p v-if="status.conflict" class="conflict-banner" data-testid="conflict-banner">
        来源验收冲突：{{ status.blocked_sources.join('、') }} 未达标，即使合并覆盖率达标也不能算进可交付批次。
        审查口径仍保留各来源实际缺值数（见下表缺值列）。
      </p>

      <table class="data-table" data-testid="source-table">
        <thead>
          <tr>
            <th>来源</th>
            <th>验收状态</th>
            <th>样本量</th>
            <th>有效行数</th>
            <th>缺值行数</th>
            <th>缺值字段数</th>
            <th>覆盖率</th>
            <th>阈值</th>
            <th>轮次</th>
            <th>最近提交方式</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="source in status.sources"
            :key="source.source"
            :data-testid="`source-row-${source.source}`"
            :data-result="source.result"
          >
            <td>{{ source.source }}</td>
            <td>
              <span class="tag" :class="source.passed ? 'tag-ok' : 'tag-bad'">{{ source.result }}</span>
            </td>
            <td>{{ source.sample_rows }}</td>
            <td>{{ source.valid_rows }}</td>
            <td>{{ source.missing_rows }}</td>
            <td>{{ source.missing_values }}</td>
            <td>
              <template v-if="source.coverage_percent !== null && source.coverage_percent !== undefined">
                {{ source.coverage_percent }}%
              </template>
              <template v-else>—</template>
            </td>
            <td>{{ source.threshold_percent }}%</td>
            <td>{{ source.rounds }}</td>
            <td>{{ source.last_mode === 'replace' ? '重新提交' : source.last_mode === 'append' ? '追加提交' : '—' }}</td>
          </tr>
          <tr v-if="!status.sources.length">
            <td colspan="10" class="empty-state">该批次还没有来源验收记录</td>
          </tr>
        </tbody>
      </table>

      <section class="rounds-panel" data-testid="rounds-panel">
        <header class="rounds-head">
          <h3>验收历史</h3>
          <label class="rounds-filter">
            <span>来源</span>
            <select v-model="roundSource" data-testid="round-source" @change="loadRounds">
              <option value="">全部来源</option>
              <option v-for="source in status.required_sources" :key="source" :value="source">
                {{ source }}
              </option>
            </select>
          </label>
        </header>
        <p class="page-desc">{{ roundHint }}</p>
        <table class="data-table" data-testid="round-table">
          <thead>
            <tr>
              <th>提交时间</th>
              <th>来源</th>
              <th>来源轮次</th>
              <th>提交方式</th>
              <th>轮次阈值</th>
              <th>本轮样本</th>
              <th>本轮有效</th>
              <th>本轮缺值行</th>
              <th>本轮结果</th>
              <th>累计样本</th>
              <th>累计有效</th>
              <th>累计覆盖率</th>
              <th>当时交付结论</th>
              <th>当时可读来源</th>
              <th>当时交付范围</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="round in rounds"
              :key="round.id"
              :data-testid="`round-row-${round.id}`"
            >
              <td>{{ round.submitted_at }}</td>
              <td>{{ round.source }}</td>
              <td>第 {{ round.source_round_no }} 次</td>
              <td>{{ round.mode === 'replace' ? '重新提交' : '追加提交' }}</td>
              <td>{{ round.threshold_percent }}%</td>
              <td>{{ round.sample_rows }}</td>
              <td>{{ round.valid_rows }}</td>
              <td>{{ round.missing_values }}</td>
              <td>
                <span class="tag" :class="round.effective_result === '通过' ? 'tag-ok' : 'tag-bad'">
                  {{ round.effective_result }}（{{ round.effective_coverage_percent }}%）
                </span>
              </td>
              <td>{{ round.effective_sample_rows }}</td>
              <td>{{ round.effective_valid_rows }}</td>
              <td>{{ round.effective_coverage_percent }}%</td>
              <td>{{ round.delivery_status }}</td>
              <td>{{ round.readable_sources.join('、') || '—' }}</td>
              <td>{{ round.deliverable_scope.join('、') || '—' }}</td>
            </tr>
            <tr v-if="!rounds.length">
              <td colspan="15" class="empty-state">还没有提交记录</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="submit-panel" data-testid="submit-panel">
        <h3>提交来源样本</h3>
        <p class="page-desc">
          追加提交会与之前的样本累加；重新提交会整体替换该来源的累计口径，历史轮次仍然可查。
          采集记录里的 price 实采为 0 算有效，缺值补出的 0 不计入有效行。
        </p>
        <form class="submit-form" @submit.prevent="submitSource">
          <label>
            <span>来源</span>
            <select v-model="submitForm.source" data-testid="submit-source-select">
              <option v-for="source in status.required_sources" :key="source" :value="source">
                {{ source }}
              </option>
            </select>
          </label>
          <label>
            <span>提交方式</span>
            <select v-model="submitForm.mode" data-testid="submit-mode">
              <option value="append">追加提交</option>
              <option value="replace">重新提交</option>
            </select>
          </label>
          <label class="submit-records">
            <span>采集记录（JSON 数组）</span>
            <textarea v-model="submitForm.records" rows="4" data-testid="submit-records" spellcheck="false" />
          </label>
          <button class="btn primary" data-testid="submit-source" type="submit" :disabled="submitting">
            {{ submitting ? '提交中…' : '提交样本' }}
          </button>
        </form>
        <p v-if="submitMessage" class="page-desc" data-testid="submit-message">{{ submitMessage }}</p>
      </section>
    </template>

    <p v-else-if="!errorMessage" class="empty-state">正在读取覆盖率验收数据…</p>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import {
  getCoverageBatch,
  getCoverageRounds,
  listCoverageBatches,
  submitCoverageSource,
  type CoverageBatchStatus,
  type CoverageBatchSummary,
  type CoverageRound,
} from '@/api/backend-service'

const batches = ref<CoverageBatchSummary[]>([])
const activeBatchId = ref('')
const status = ref<CoverageBatchStatus | null>(null)
const rounds = ref<CoverageRound[]>([])
const roundSource = ref('')
const errorMessage = ref('')
const submitMessage = ref('')
const submitting = ref(false)
const submitForm = ref({
  source: '',
  mode: 'append' as 'append' | 'replace',
  records: '[{"price": 0}, {"price": ""}, {"price": 22}]',
})

const roundHint = computed(() => {
  if (!rounds.value.length) return '按来源查看每一次提交的完整验收口径和当时的交付范围。'
  const first = rounds.value[0]
  return `最近一次提交：${first.submitted_at}，${first.source} 第 ${first.source_round_no} 次提交；重建提交不会覆盖历史阈值记录。`
})

async function loadRounds() {
  if (!activeBatchId.value) return
  errorMessage.value = ''
  try {
    const payload = await getCoverageRounds(activeBatchId.value, roundSource.value || undefined)
    rounds.value = payload.rounds
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '验收历史读取失败'
  }
}

async function loadBatch() {
  if (!activeBatchId.value) return
  errorMessage.value = ''
  submitMessage.value = ''
  try {
    status.value = await getCoverageBatch(activeBatchId.value)
    if (!status.value.required_sources.includes(submitForm.value.source)) {
      submitForm.value.source = status.value.required_sources[0] ?? ''
    }
    await loadRounds()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '验收批次读取失败'
  }
}

async function submitSource() {
  if (!activeBatchId.value || !status.value) return
  submitting.value = true
  errorMessage.value = ''
  submitMessage.value = ''
  try {
    let records: Record<string, unknown>[]
    try {
      records = JSON.parse(submitForm.value.records)
    } catch {
      throw new Error('采集记录必须是合法的 JSON 数组')
    }
    if (!Array.isArray(records)) throw new Error('采集记录必须是 JSON 数组')
    const result = await submitCoverageSource(activeBatchId.value, {
      source: submitForm.value.source,
      mode: submitForm.value.mode,
      records,
    })
    const message =
      `${result.record.source} 第 ${result.record.source_round_no} 次提交：` +
      `本轮 ${result.record.valid_rows}/${result.record.sample_rows}，` +
      `累计 ${result.record.effective_valid_rows}/${result.record.effective_sample_rows}` +
      `（${result.record.effective_result}）；当前批次${result.batch.delivery_status}。`
    // loadBatch 会清空提示，先刷新再回填本次提交的结论。
    await loadBatch()
    submitMessage.value = message
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '来源样本提交失败'
  } finally {
    submitting.value = false
  }
}

async function reloadAll() {
  errorMessage.value = ''
  try {
    batches.value = await listCoverageBatches()
    if (!batches.value.some((batch) => batch.batch_id === activeBatchId.value)) {
      activeBatchId.value = batches.value[0]?.batch_id ?? ''
    }
    await loadBatch()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '验收批次读取失败'
  }
}

onMounted(reloadAll)
</script>

<style scoped>
.stat-value.ok { color: #15803d; }
.stat-value.bad { color: #b42318; }
.batch-picker { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--muted); }
.batch-picker select { padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; }
.delivery-banner { padding: 10px 12px; border-radius: 8px; font-size: 13px; margin: 0 0 10px; }
.delivery-banner.ok { background: #ecfdf3; border: 1px solid #a7f3d0; color: #166534; }
.delivery-banner.bad { background: #fef3f2; border: 1px solid #fecdca; color: #b42318; }
.conflict-banner { padding: 10px 12px; border-radius: 8px; font-size: 13px; margin: 0 0 12px; background: #fffaeb; border: 1px solid #fedf89; color: #93370d; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; }
.tag-ok { background: #ecfdf3; color: #166534; }
.tag-bad { background: #fef3f2; color: #b42318; }
.rounds-panel { margin-top: 18px; }
.rounds-head { display: flex; justify-content: space-between; align-items: flex-end; }
.rounds-head h3 { margin: 0 0 4px; font-size: 15px; }
.rounds-filter { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--muted); }
.rounds-filter select { padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; }
.submit-panel { margin-top: 18px; background: #fff; border: 1px solid var(--border); border-radius: 8px; padding: 12px; }
.submit-panel h3 { margin: 0 0 4px; font-size: 15px; }
.submit-form { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-end; margin-top: 10px; }
.submit-form label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--muted); }
.submit-form select { padding: 6px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 13px; }
.submit-records { flex: 1; min-width: 280px; }
.submit-records textarea { width: 100%; border: 1px solid var(--border); border-radius: 6px; padding: 8px; font-family: monospace; font-size: 12px; resize: vertical; }
</style>
