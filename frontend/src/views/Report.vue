<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '../stores/chat'
import { useCatalogStore, ROLE_NAMES } from '../stores/catalog'
import { getGrowthSummary, getRoutingMetrics } from '../api'
import { toast } from '../utils/toast'
import RadarChart from '../components/RadarChart.vue'
import Icon from '../components/Icon.vue'

const router = useRouter()
const chat = useChatStore()
const catalog = useCatalogStore()

const growth = ref(null)
const routing = ref(null)
const extrasLoading = ref(false)
const showCompare = ref(true)

const ev = computed(() => chat.evaluation)
const isFailed = computed(() => ev.value?.status === 'failed')
const directionText = computed(() => chat.directionName || catalog.nameOf(chat.direction))
const roleText = computed(() => ROLE_NAMES[chat.role] || chat.role)
const confidence = computed(() => Math.round((ev.value?.confidence || 0) * 100))

const citations = computed(() => ev.value?.knowledge_evidence || chat.interviewMessages.flatMap((m) => m.retrieval || []))
const statusLabel = computed(() => ({ completed: '正式评估', failed: '反馈待重试', demo: '演示报告' }[ev.value?.status] || ev.value?.status || '未知状态'))
const statusTone = computed(() => ({ completed: 'success', failed: 'danger', demo: 'warning' }[ev.value?.status] || 'info'))
const evidenceMessages = computed(() => Object.fromEntries(
  chat.interviewMessages.filter((m) => m.role === 'user').map((m) => [m.message_id, m.content])
))
const evidenceMap = computed(() => Object.fromEntries((ev.value?.evidence || []).map((item) => [item.message_id, item])))

function toneOf(score) {
  if (score >= 75) return 'success'
  if (score >= 60) return 'warning'
  return 'danger'
}

const scoreTone = computed(() => toneOf(ev.value?.overall_score || 0))
const scoreLevel = computed(() => {
  if (!ev.value) return ''
  const s = ev.value.overall_score
  if (s >= 85) return '优秀 · 稳拿 offer'
  if (s >= 75) return '良好 · 略有短板'
  if (s >= 60) return '及格 · 需要补强'
  return '待提升 · 重点迭代'
})

// 圆环进度：周长 2πr，r=52
const RING = 2 * Math.PI * 52
const ringOffset = computed(() => RING * (1 - Math.min(100, Math.max(0, ev.value?.overall_score || 0)) / 100))

const sortedDims = computed(() => [...(ev.value?.dimensions || [])].sort((a, b) => b.score - a.score))
const bestDim = computed(() => sortedDims.value[0] || null)
const worstDim = computed(() => sortedDims.value[sortedDims.value.length - 1] || null)

const hasGrowth = computed(() => Boolean(growth.value?.previous_session_id))
// 由当前分与变化值反推上一场维度分，用于雷达图对比
const compareDims = computed(() => {
  if (!hasGrowth.value || !showCompare.value) return []
  const changes = growth.value.dimension_changes || {}
  return (ev.value?.dimensions || [])
    .filter((d) => typeof changes[d.name] === 'number')
    .map((d) => ({ name: d.name, score: Math.max(0, Math.min(100, d.score - changes[d.name])) }))
})

const savedRatio = computed(() => {
  const r = routing.value
  if (!r?.full_strong_model_cost) return 0
  return Math.round(((r.saved_cost || 0) / r.full_strong_model_cost) * 100)
})
const modelCalls = computed(() => Object.entries(routing.value?.model_calls || {}))
const routeReasons = computed(() => Object.entries(routing.value?.route_reasons || {}))

function signed(n) {
  const v = Number(n) || 0
  return `${v > 0 ? '+' : ''}${Math.round(v * 10) / 10}`
}

async function loadExtras() {
  if (!chat.sessionId || !ev.value || isFailed.value) return
  extrasLoading.value = true
  const sid = chat.sessionId
  await Promise.all([
    getGrowthSummary(sid).then((d) => { growth.value = d }).catch(() => { growth.value = null }),
    getRoutingMetrics(sid).then((d) => { routing.value = d && d.calls ? d : null }).catch(() => { routing.value = null })
  ])
  extrasLoading.value = false
}

onMounted(() => {
  if (!catalog.loaded) catalog.load?.().catch(() => {})
  loadExtras()
})
watch(() => [chat.sessionId, ev.value?.status], loadExtras)

async function retry() {
  const result = await chat.runEvaluation()
  if (result?.status === 'failed') toast('反馈仍未生成，请稍后再试', 'warning')
  else toast('评估报告已生成', 'success')
}

function newInterview() {
  chat.reset()
  router.push('/chat')
}

function pad(n) { return String(n).padStart(2, '0') }
function makeTimestamp(d = new Date()) {
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
}
function formatTime(d) {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

function exportReport() {
  if (!ev.value) return
  const e = ev.value
  const lines = [
    '# 面试评估报告', '',
    `- 状态:${statusLabel.value}`,
    `- 置信度:${confidence.value}%`,
    `- 总分:${e.overall_score.toFixed(0)} / 100`,
    `- 方向:${directionText.value}`,
    `- 角色:${roleText.value}`,
    `- 时间:${formatTime(new Date())}`
  ]
  if (e.warnings?.length) {
    lines.push('', '## 警告')
    e.warnings.forEach((w) => lines.push(`- ${w}`))
  }
  lines.push('', '## 维度评分')
  for (const d of (e.dimensions || [])) {
    lines.push(`- ${d.name}:${d.score}`)
    if (d.evidence_ids?.length) lines.push(`  - 证据:${d.evidence_ids.join('、')}`)
  }
  const section = (title, list) => {
    lines.push('', `## ${title}`)
    for (const s of (list || [])) lines.push(`- ${s}`)
  }
  section('亮点', e.strengths)
  section('短板', e.weaknesses)
  section('改进建议', e.suggestions)
  lines.push('', '## 总评', e.summary || '', '', '## 评估证据')
  for (const item of (e.evidence || [])) {
    lines.push(`- [${item.message_id}] ${item.claim}`)
    lines.push(`  - 引用:${item.quote}`)
    if (evidenceMessages.value[item.message_id]) lines.push(`  - 原回答:${evidenceMessages.value[item.message_id]}`)
  }
  lines.push('')
  const blob = new Blob([lines.join('\n')], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `评估报告_${makeTimestamp()}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
  toast('报告已导出', 'success')
}
</script>

<template>
  <div class="container report-page">
    <header class="page-head">
      <div>
        <div class="eyebrow">Evaluation Report</div>
        <h1 class="page-title">评估报告</h1>
        <p class="page-sub">基于整场面试对话的 AI 评估，逐条关联你的原回答，帮你定位短板、迭代提升</p>
      </div>
      <div v-if="ev && !chat.evaluating" class="row gap-2 wrap">
        <button v-if="!isFailed" class="btn btn-secondary" @click="exportReport">
          <Icon name="download" :size="16" /> 导出报告
        </button>
        <button class="btn btn-gradient" @click="newInterview">
          <Icon name="play" :size="16" /> 再来一场
        </button>
      </div>
    </header>

    <!-- 评估中 -->
    <section v-if="chat.evaluating" class="card empty">
      <div class="spinner lg"></div>
      <div class="empty-title mt-4">正在生成评估报告…</div>
      <div class="empty-desc">AI 正在逐条分析你的回答、关联证据并计算各维度得分</div>
      <div class="loading-steps mt-4">
        <span><Icon name="message" :size="14" /> 读取对话</span>
        <Icon name="chevronRight" :size="14" class="text-dim" />
        <span><Icon name="target" :size="14" /> 维度打分</span>
        <Icon name="chevronRight" :size="14" class="text-dim" />
        <span><Icon name="bulb" :size="14" /> 生成建议</span>
      </div>
    </section>

    <!-- 空状态 -->
    <section v-else-if="!ev" class="card empty">
      <div class="empty-icon"><Icon name="report" :size="32" /></div>
      <div class="empty-title">还没有评估报告</div>
      <div class="empty-desc">完成一场模拟面试后，点击「结束并评估」即可生成带证据的评估报告</div>
      <div class="row gap-2 mt-4" style="justify-content: center">
        <button class="btn btn-primary" @click="router.push('/chat')"><Icon name="message" :size="16" /> 去面试间</button>
        <button class="btn btn-secondary" @click="router.push('/')"><Icon name="history" :size="16" /> 查看历史记录</button>
      </div>
    </section>

    <template v-else>
      <!-- 状态提示 -->
      <div v-if="ev.status !== 'completed'" class="alert" :class="`alert-${statusTone}`">
        <Icon class="alert-icon" :name="isFailed ? 'xCircle' : 'info'" :size="18" />
        <div class="flex-1">
          <strong>{{ statusLabel }}</strong>
          <div class="text-sm">
            {{ ev.status === 'demo' ? '当前为演示模式，结果不计入正式成绩，也不会保存。配置模型密钥后可获得正式评估。' : '反馈暂时无法生成，你的对话已完整保留，可以稍后重试。' }}
          </div>
          <ul v-if="ev.warnings?.length && !isFailed" class="warn-list">
            <li v-for="(w, i) in ev.warnings" :key="i">{{ w }}</li>
          </ul>
        </div>
      </div>
      <div v-else-if="ev.warnings?.length" class="alert alert-warning">
        <Icon class="alert-icon" name="alert" :size="18" />
        <ul class="warn-list flex-1">
          <li v-for="(w, i) in ev.warnings" :key="i">{{ w }}</li>
        </ul>
      </div>

      <!-- 失败 -->
      <section v-if="isFailed" class="card empty">
        <div class="empty-icon"><Icon name="refresh" :size="30" /></div>
        <div class="empty-title">回答已保留</div>
        <div class="empty-desc">{{ ev.summary || '反馈暂时无法生成，你可以继续练习，稍后再试。' }}</div>
        <div class="row gap-2 mt-4" style="justify-content: center">
          <button class="btn btn-primary" :disabled="chat.evaluating" @click="retry">
            <Icon name="refresh" :size="16" /> 重新生成反馈
          </button>
          <button class="btn btn-secondary" @click="router.push('/chat')">返回面试间</button>
        </div>
      </section>

      <template v-else>
        <!-- 总览 -->
        <section class="card overview">
          <div class="score-block">
            <div class="ring" :class="`tone-${scoreTone}`">
              <svg viewBox="0 0 120 120" aria-hidden="true">
                <circle cx="60" cy="60" r="52" class="ring-bg" />
                <circle cx="60" cy="60" r="52" class="ring-fg" :stroke-dasharray="RING" :stroke-dashoffset="ringOffset" />
              </svg>
              <div class="ring-center">
                <div class="ring-num">{{ ev.overall_score.toFixed(0) }}</div>
                <div class="ring-unit">/ 100</div>
              </div>
            </div>
            <div class="score-level" :class="`text-${scoreTone}`">{{ scoreLevel }}</div>
            <div v-if="hasGrowth" class="text-sm mt-1" :class="growth.overall_score_change >= 0 ? 'text-success' : 'text-danger'">
              <Icon :name="growth.overall_score_change >= 0 ? 'trendUp' : 'trendDown'" :size="14" />
              较上一场 {{ signed(growth.overall_score_change) }}
            </div>
          </div>

          <div class="meta-block">
            <div class="row gap-2 wrap">
              <span class="tag" :class="`tag-${statusTone}`"><span class="dot" :class="`dot-${statusTone}`"></span>{{ statusLabel }}</span>
              <span class="tag">置信度 {{ confidence }}%</span>
              <span v-if="chat.sessionId && ev.status === 'completed'" class="tag tag-success"><Icon name="checkCircle" :size="12" /> 已保存到历史</span>
              <span v-else-if="ev.status === 'demo'" class="tag tag-warning">演示报告不保存</span>
            </div>
            <dl class="meta-list">
              <div><dt><Icon name="briefcase" :size="14" /> 面试岗位</dt><dd class="truncate" :title="directionText">{{ directionText }}</dd></div>
              <div><dt><Icon name="users" :size="14" /> 面试类型</dt><dd>{{ roleText }}</dd></div>
              <div><dt><Icon name="message" :size="14" /> 回答轮次</dt><dd>{{ chat.answerCount }} 轮</dd></div>
              <div><dt><Icon name="layers" :size="14" /> 评估维度</dt><dd>{{ ev.dimensions?.length || 0 }} 项</dd></div>
            </dl>
            <div v-if="bestDim && worstDim && bestDim !== worstDim" class="highlights">
              <div class="hl hl-good">
                <Icon name="award" :size="16" />
                <div><div class="text-xs text-soft">最强维度</div><strong>{{ bestDim.name }} · {{ bestDim.score.toFixed(0) }}</strong></div>
              </div>
              <div class="hl hl-bad">
                <Icon name="target" :size="16" />
                <div><div class="text-xs text-soft">优先补强</div><strong>{{ worstDim.name }} · {{ worstDim.score.toFixed(0) }}</strong></div>
              </div>
            </div>
          </div>

          <div class="radar-block">
            <div class="row">
              <span class="text-sm text-soft">能力雷达</span>
              <div v-if="compareDims.length || (hasGrowth && !showCompare)" class="row gap-2 ml-auto text-xs">
                <label class="switch">
                  <input v-model="showCompare" type="checkbox" />
                </label>
                <span>对比上一场</span>
              </div>
            </div>
            <RadarChart v-if="ev.dimensions?.length" :dimensions="ev.dimensions" :compare="compareDims" :height="280" />
            <div v-else class="empty-desc">暂无维度数据</div>
          </div>
        </section>

        <!-- 总评 -->
        <section v-if="ev.summary" class="card summary-card">
          <Icon name="quote" :size="22" class="text-primary" />
          <div>
            <div class="section-title">面试官总评</div>
            <p class="summary">{{ ev.summary }}</p>
          </div>
        </section>

        <!-- 维度详情 -->
        <section v-if="ev.dimensions?.length" class="card">
          <div class="section-title"><Icon name="chart" :size="18" /> 维度详情</div>
          <div class="dim-list">
            <article v-for="d in ev.dimensions" :key="d.name" class="dim-item">
              <div class="row">
                <span class="dim-name">{{ d.name }}</span>
                <span v-if="hasGrowth && typeof growth.dimension_changes?.[d.name] === 'number'" class="text-xs"
                  :class="growth.dimension_changes[d.name] >= 0 ? 'text-success' : 'text-danger'">
                  {{ signed(growth.dimension_changes[d.name]) }}
                </span>
                <span class="dim-score ml-auto" :class="`text-${toneOf(d.score)}`">{{ d.score.toFixed(0) }}</span>
              </div>
              <div class="progress mt-2" :class="`progress-${toneOf(d.score)}`"><span :style="{ width: d.score + '%' }"></span></div>
              <p v-if="d.comment" class="text-soft text-sm mt-2 lh">{{ d.comment }}</p>
              <div v-if="d.evidence_ids?.length" class="evidence mt-2">
                <details v-for="id in d.evidence_ids" :key="id">
                  <summary><Icon name="fileText" :size="13" /> {{ evidenceMap[id]?.claim || '查看关联证据' }}</summary>
                  <blockquote v-if="evidenceMap[id]?.quote">“{{ evidenceMap[id].quote }}”</blockquote>
                  <p v-if="evidenceMessages[id]" class="text-soft text-sm"><b>你的原回答：</b>{{ evidenceMessages[id] }}</p>
                </details>
              </div>
            </article>
          </div>
        </section>

        <!-- 亮点 / 短板 / 建议 -->
        <section class="grid-3">
          <div class="card point-card tone-success">
            <div class="section-title"><Icon name="sparkles" :size="18" /> 亮点</div>
            <ul v-if="ev.strengths?.length" class="point-list">
              <li v-for="(s, i) in ev.strengths" :key="i"><Icon name="check" :size="14" />{{ s }}</li>
            </ul>
            <p v-else class="text-dim text-sm">暂无</p>
          </div>
          <div class="card point-card tone-danger">
            <div class="section-title"><Icon name="alert" :size="18" /> 短板</div>
            <ul v-if="ev.weaknesses?.length" class="point-list">
              <li v-for="(s, i) in ev.weaknesses" :key="i"><Icon name="flag" :size="14" />{{ s }}</li>
            </ul>
            <p v-else class="text-dim text-sm">暂无</p>
          </div>
          <div class="card point-card tone-primary">
            <div class="section-title"><Icon name="bulb" :size="18" /> 改进建议</div>
            <ol v-if="ev.suggestions?.length" class="point-list numbered">
              <li v-for="(s, i) in ev.suggestions" :key="i"><span class="num">{{ i + 1 }}</span>{{ s }}</li>
            </ol>
            <p v-else class="text-dim text-sm">暂无</p>
          </div>
        </section>

        <!-- 跨场对比 -->
        <section v-if="hasGrowth" class="card">
          <div class="section-title"><Icon name="trendUp" :size="18" /> 成长对比</div>
          <div class="grid-4">
            <div class="stat">
              <div class="stat-label">总分变化</div>
              <div class="stat-value" :class="growth.overall_score_change >= 0 ? 'text-success' : 'text-danger'">{{ signed(growth.overall_score_change) }}</div>
            </div>
            <div v-if="growth.coach_dependency" class="stat">
              <div class="stat-label">辅导求助次数</div>
              <div class="stat-value">{{ growth.coach_dependency.previous }} → {{ growth.coach_dependency.current }}</div>
              <div class="stat-foot">{{ growth.coach_dependency.current <= growth.coach_dependency.previous ? '独立作答能力提升' : '本场更依赖辅导' }}</div>
            </div>
            <div class="stat span-2">
              <div class="stat-label">维度变化</div>
              <div class="row gap-2 wrap mt-2">
                <span v-for="(change, name) in growth.dimension_changes" :key="name" class="tag" :class="change >= 0 ? 'tag-success' : 'tag-danger'">
                  {{ name }} {{ signed(change) }}
                </span>
              </div>
            </div>
          </div>
          <div v-if="growth.repeated_weaknesses?.length" class="alert alert-warning mt-4">
            <Icon class="alert-icon" name="history" :size="18" />
            <div><strong>反复出现的短板：</strong>{{ growth.repeated_weaknesses.join('、') }}。建议在题库中针对性练习。</div>
            <button class="btn btn-sm btn-secondary ml-auto" @click="router.push('/questions')">去题库</button>
          </div>
        </section>

        <!-- 资料引用 -->
        <section v-if="citations.length" class="card">
          <div class="section-title"><Icon name="database" :size="18" /> 检索依据 / 资料引用</div>
          <div class="citation-list">
            <div v-for="(c, i) in citations" :key="c.chunk_id || i" class="citation">
              <div class="row gap-2 wrap">
                <span class="tag tag-primary"><Icon name="file" :size="12" /> {{ c.source || '资料' }}</span>
                <span class="tag">{{ c.document_type || 'other' }}</span>
                <span v-if="c.page" class="text-xs text-soft">第 {{ c.page }} 页</span>
                <span v-if="c.line" class="text-xs text-soft">第 {{ c.line }} 行</span>
                <span class="text-xs text-soft ml-auto">相关度 {{ Math.round((c.score || 0) * 100) }}%</span>
              </div>
              <p v-if="c.excerpt || c.quote" class="text-sm text-soft mt-2 clamp-2">{{ c.excerpt || c.quote }}</p>
            </div>
          </div>
        </section>

        <!-- 路由数据 -->
        <section v-if="routing" class="card">
          <div class="section-title"><Icon name="route" :size="18" /> 本场模型路由</div>
          <div class="grid-4">
            <div class="stat"><div class="stat-label">调用次数</div><div class="stat-value">{{ routing.calls || 0 }}</div></div>
            <div class="stat"><div class="stat-label">Token</div><div class="stat-value">{{ (routing.total_tokens || 0).toLocaleString() }}</div></div>
            <div class="stat"><div class="stat-label">平均延迟</div><div class="stat-value">{{ Math.round(routing.average_latency_ms || 0) }}<small>ms</small></div></div>
            <div class="stat">
              <div class="stat-label">较全程强模型节省</div>
              <div class="stat-value text-success">{{ savedRatio }}%</div>
              <div class="stat-foot">估算成本 {{ routing.estimated_cost || 0 }} · 节省 {{ routing.saved_cost || 0 }}</div>
            </div>
          </div>
          <div class="grid-2 mt-4">
            <div>
              <div class="text-xs text-soft mb-2">模型调用分布</div>
              <div class="row gap-2 wrap">
                <span v-for="[m, n] in modelCalls" :key="m" class="tag"><Icon name="cpu" :size="12" /> {{ m }} × {{ n }}</span>
                <span v-if="!modelCalls.length" class="text-dim text-sm">暂无记录</span>
              </div>
            </div>
            <div>
              <div class="text-xs text-soft mb-2">路由原因</div>
              <div class="row gap-2 wrap">
                <span v-for="[r, n] in routeReasons" :key="r" class="tag">{{ r }} × {{ n }}</span>
                <span v-if="!routeReasons.length" class="text-dim text-sm">暂无记录</span>
              </div>
            </div>
          </div>
        </section>
        <div v-else-if="extrasLoading" class="skeleton" style="height: 120px"></div>

        <!-- 下一步 -->
        <section class="card next-card">
          <div>
            <div class="section-title">下一步</div>
            <p class="text-soft text-sm">针对短板继续练习，或补充简历 / JD 让面试官的追问更贴近真实岗位。</p>
          </div>
          <div class="row gap-2 wrap">
            <button class="btn btn-gradient" @click="newInterview"><Icon name="play" :size="16" /> 再来一场</button>
            <button class="btn btn-secondary" @click="router.push('/questions')"><Icon name="library" :size="16" /> 题库专项练习</button>
            <button class="btn btn-ghost" @click="router.push('/knowledge')"><Icon name="upload" :size="16" /> 补充资料</button>
            <button class="btn btn-ghost" @click="exportReport"><Icon name="download" :size="16" /> 导出</button>
          </div>
        </section>
      </template>
    </template>
  </div>
</template>

<style scoped>
.report-page { display: flex; flex-direction: column; gap: 16px; }
.loading-steps { display: inline-flex; align-items: center; gap: 10px; color: var(--text-soft); font-size: 13px; }
.loading-steps span { display: inline-flex; align-items: center; gap: 4px; }
.spinner.lg { width: 36px; height: 36px; border-width: 3px; margin: 0 auto; }
.warn-list { margin: 6px 0 0; padding-left: 18px; font-size: 13px; }

.overview { display: grid; grid-template-columns: 200px 1fr 1.2fr; gap: 24px; align-items: center; }
.score-block { text-align: center; }
.ring { position: relative; width: 148px; height: 148px; margin: 0 auto; }
.ring svg { width: 100%; height: 100%; transform: rotate(-90deg); }
.ring circle { fill: none; stroke-width: 10; }
.ring-bg { stroke: var(--bg-hover); }
.ring-fg { stroke-linecap: round; transition: stroke-dashoffset 0.9s cubic-bezier(.2,.8,.2,1); }
.tone-success .ring-fg { stroke: var(--success); }
.tone-warning .ring-fg { stroke: var(--warning); }
.tone-danger .ring-fg { stroke: var(--danger); }
.ring-center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.ring-num { font-size: 44px; font-weight: 800; line-height: 1; letter-spacing: -1px; }
.ring-unit { font-size: 12px; color: var(--text-dim); margin-top: 2px; }
.score-level { font-weight: 600; margin-top: 10px; }

.meta-list { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin: 16px 0; }
.meta-list dt { display: flex; align-items: center; gap: 4px; font-size: 12px; color: var(--text-dim); }
.meta-list dd { margin: 4px 0 0; font-weight: 600; }
.highlights { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.hl { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: var(--radius-sm); font-size: 13px; }
.hl-good { background: var(--success-bg); color: var(--success); }
.hl-bad { background: var(--danger-bg); color: var(--danger); }
.hl strong { color: var(--text); }

.summary-card { display: flex; gap: 14px; align-items: flex-start; }
.summary { line-height: 1.8; color: var(--text-soft); margin: 0; }
.section-title { display: flex; align-items: center; gap: 8px; }

.dim-list { display: grid; grid-template-columns: 1fr 1fr; gap: 14px 24px; }
.dim-item { padding: 14px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg); }
.dim-name { font-weight: 600; margin-right: 8px; }
.dim-score { font-weight: 800; font-size: 20px; }
.lh { line-height: 1.65; margin-bottom: 0; }
.progress-success > span { background: var(--success); }
.progress-warning > span { background: var(--warning); }
.progress-danger > span { background: var(--danger); }
.evidence details { border-top: 1px dashed var(--border); padding: 6px 0; font-size: 13px; }
.evidence summary { cursor: pointer; color: var(--primary); display: flex; align-items: center; gap: 6px; list-style: none; }
.evidence summary::-webkit-details-marker { display: none; }
.evidence blockquote { margin: 8px 0; padding: 6px 10px; border-left: 3px solid var(--primary); background: var(--bg-hover); border-radius: 4px; color: var(--text); }

.point-card .section-title { margin-bottom: 10px; }
.point-card.tone-success .section-title { color: var(--success); }
.point-card.tone-danger .section-title { color: var(--danger); }
.point-card.tone-primary .section-title { color: var(--primary); }
.point-list { list-style: none; padding: 0; margin: 0; }
.point-list li { display: flex; gap: 8px; padding: 9px 0; border-bottom: 1px solid var(--border); font-size: 14px; line-height: 1.6; }
.point-list li:last-child { border-bottom: none; }
.point-list li > :first-child { flex-shrink: 0; margin-top: 4px; }
.point-list .num { width: 20px; height: 20px; margin-top: 1px !important; border-radius: 50%; background: var(--info-bg); color: var(--primary); font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center; }

.span-2 { grid-column: span 2; }
.stat-value small { font-size: 13px; color: var(--text-dim); margin-left: 2px; }
.citation-list { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.citation { padding: 12px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg); }
.citation p { margin-bottom: 0; }

.next-card { display: flex; align-items: center; justify-content: space-between; gap: 16px; flex-wrap: wrap; background: var(--gradient-hero); }
.next-card p { margin: 0; }

@media (max-width: 1100px) {
  .overview { grid-template-columns: 180px 1fr; }
  .radar-block { grid-column: 1 / -1; }
}
@media (max-width: 768px) {
  .overview { grid-template-columns: 1fr; }
  .dim-list, .citation-list { grid-template-columns: 1fr; }
  .span-2 { grid-column: auto; }
  .highlights { grid-template-columns: 1fr; }
}
</style>
