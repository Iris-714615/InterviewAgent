<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '../stores/chat'
import { getGrowthSummary } from '../api'
import { ref, onMounted } from 'vue'
import RadarChart from '../components/RadarChart.vue'

const router = useRouter()
const chat = useChatStore()
const growth = ref(null)
const growthLoading = ref(false)

const ev = computed(() => chat.evaluation)
const citations = computed(() => ev.value?.knowledge_evidence || chat.interviewMessages.flatMap((m) => m.retrieval || []))
onMounted(async () => {
  if (chat.sessionId) {
    growthLoading.value = true
    try { growth.value = await getGrowthSummary(chat.sessionId) } catch (e) { growth.value = null } finally { growthLoading.value = false }
  }
})
const statusLabel = computed(() => ({ completed: '正式评估', failed: '评估失败', demo: '演示报告' }[ev.value?.status] || ev.value?.status || '未知状态'))
const evidenceMessages = computed(() => Object.fromEntries(
  chat.interviewMessages.filter((m) => m.role === 'user').map((m) => [m.message_id, m.content])
))
const evidenceMap = computed(() => Object.fromEntries((ev.value?.evidence || []).map((item) => [item.message_id, item])))
const scoreColor = computed(() => {
  if (!ev.value) return 'var(--text-soft)'
  const s = ev.value.overall_score
  if (s >= 80) return 'var(--success)'
  if (s >= 60) return 'var(--warning)'
  return 'var(--danger)'
})
const scoreLevel = computed(() => {
  if (!ev.value) return ''
  const s = ev.value.overall_score
  if (s >= 85) return '优秀 · 稳拿 offer'
  if (s >= 75) return '良好 · 略有短板'
  if (s >= 60) return '及格 · 需要补强'
  return '待提升 · 重点迭代'
})

// 方向中文映射
const directionMap = {
  ai_app_engineer: 'AI大模型应用工程师',
  ai_dev_engineer: 'AI应用开发工程师',
  ai_product_manager: 'AI产品经理'
}
// 角色中文映射
const roleMap = {
  technical: '技术面',
  hr: 'HR面',
  behavioral: '行为面'
}

// 生成时间戳 YYYYMMDD_HHmmss
function makeTimestamp() {
  const d = new Date()
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}${pad(d.getSeconds())}`
}

// 格式化时间 YYYY-MM-DD HH:mm:ss
function formatTime(d) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

// 导出评估报告为 Markdown 文件
function exportReport() {
  if (!ev.value) return
  const now = new Date()
  const e = ev.value
  const directionText = directionMap[chat.direction] || chat.direction
  const roleText = roleMap[chat.role] || chat.role
  const lines = []
  lines.push('# 面试评估报告')
  lines.push('')
  lines.push(`- 状态:${statusLabel.value}`)
  lines.push(`- 置信度:${Math.round((e.confidence || 0) * 100)}%`)
  lines.push(`- 总分:${e.overall_score.toFixed(0)} / 100`)
  lines.push(`- 方向:${directionText}`)
  lines.push(`- 角色:${roleText}`)
  lines.push(`- 时间:${formatTime(now)}`)
  if (e.warnings?.length) {
    lines.push('')
    lines.push('## 警告')
    e.warnings.forEach((warning) => lines.push(`- ${warning}`))
  }
  lines.push('')
  lines.push('## 维度评分')
  for (const d of (e.dimensions || [])) {
    lines.push(`- ${d.name}:${d.score}`)
    if (d.evidence_ids?.length) lines.push(`  - 证据:${d.evidence_ids.join('、')}`)
  }
  lines.push('')
  lines.push('## 亮点')
  for (const s of (e.strengths || [])) {
    lines.push(`- ${s}`)
  }
  lines.push('')
  lines.push('## 短板')
  for (const s of (e.weaknesses || [])) {
    lines.push(`- ${s}`)
  }
  lines.push('')
  lines.push('## 改进建议')
  for (const s of (e.suggestions || [])) {
    lines.push(`- ${s}`)
  }
  lines.push('')
  lines.push('## 总评')
  lines.push(e.summary || '')
  lines.push('')
  lines.push('## 评估证据')
  for (const item of (e.evidence || [])) {
    lines.push(`- [${item.message_id}] ${item.claim}`)
    lines.push(`  - 引用:${item.quote}`)
    if (evidenceMessages.value[item.message_id]) lines.push(`  - 原回答:${evidenceMessages.value[item.message_id]}`)
  }
  lines.push('')
  const md = lines.join('\n')
  const blob = new Blob([md], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `评估报告_${makeTimestamp()}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
</script>

<template>
  <div class="report-page">
    <div class="page-title">评估报告</div>
    <div class="page-sub">基于整场面试对话的 AI 评估,帮你定位短板、迭代提升</div>

    <!-- 空状态 -->
    <div v-if="!ev && !chat.evaluating" class="card empty">
      <div class="empty-icon">📊</div>
      <div class="empty-title">还没有评估报告</div>
      <div class="empty-desc text-soft">完成一场模拟面试后,点击「结束并评估」生成报告</div>
      <button class="btn btn-primary mt-4" @click="router.push('/chat')">去面试间</button>
    </div>

    <!-- 评估中 -->
    <div v-else-if="chat.evaluating" class="card empty">
      <div class="empty-icon">⏳</div>
      <div class="empty-title">正在生成评估报告…</div>
      <div class="empty-desc text-soft">AI 正在分析你的整场面试表现</div>
    </div>

    <!-- 报告内容 -->
    <template v-else-if="ev">
      <div class="card report-status" :class="`status-${ev.status}`">
        <div><strong>{{ statusLabel }}</strong> · 置信度 {{ Math.round((ev.confidence || 0) * 100) }}%</div>
        <div v-if="ev.status !== 'completed'" class="status-note">
          {{ ev.status === 'demo' ? '演示结果不计入正式成绩，也不会保存。' : '本次评估未通过解析或证据校验，不计入正式成绩。' }}
        </div>
        <ul v-if="ev.warnings?.length" class="warning-list">
          <li v-for="(warning, i) in ev.warnings" :key="i">{{ warning }}</li>
        </ul>
      </div>
      <!-- 总分 -->
      <div class="card score-card">
        <div class="score-left">
          <div class="score-label">综合评分</div>
          <div class="score-num" :style="{ color: scoreColor }">{{ ev.overall_score.toFixed(0) }}</div>
          <div class="score-level" :style="{ color: scoreColor }">{{ scoreLevel }}</div>
          <div class="save-badge" v-if="chat.sessionId && ev.status === 'completed'">
            <span class="save-icon">✓</span>
            已保存到历史记录
          </div>
          <div class="not-saved-badge" v-else-if="ev.status === 'failed' || ev.status === 'demo'">
            {{ ev.status === 'demo' ? '演示报告不保存' : '失败报告不保存' }}
          </div>
        </div>
        <div class="score-right">
          <RadarChart :dimensions="ev.dimensions" />
        </div>
      </div>

      <!-- 维度详情 -->
      <div class="card">
        <div class="section-title">维度详情</div>
        <div class="dim-list">
          <div v-for="d in ev.dimensions" :key="d.name" class="dim-item">
            <div class="dim-head">
              <span class="dim-name">{{ d.name }}</span>
              <span class="dim-score" :style="{ color: d.score >= 75 ? 'var(--success)' : d.score >= 60 ? 'var(--warning)' : 'var(--danger)' }">
                {{ d.score.toFixed(0) }}
              </span>
            </div>
            <div class="dim-bar">
              <div class="dim-bar-fill" :style="{ width: d.score + '%', background: d.score >= 75 ? 'var(--success)' : d.score >= 60 ? 'var(--warning)' : 'var(--danger)' }"></div>
            </div>
            <div class="dim-comment text-soft text-sm">{{ d.comment }}</div>
            <div v-if="d.evidence_ids?.length" class="dim-evidence">
              <details v-for="id in d.evidence_ids" :key="id">
                <summary>{{ evidenceMap[id]?.claim || '查看关联证据' }}</summary>
                <blockquote v-if="evidenceMap[id]?.quote">“{{ evidenceMap[id].quote }}”</blockquote>
                <p v-if="evidenceMessages[id]">原回答：{{ evidenceMessages[id] }}</p>
              </details>
            </div>
          </div>
        </div>
      </div>

      <!-- 亮点 / 短板 / 建议 -->
      <div class="grid-3">
        <div class="card col">
          <div class="section-title" style="color: var(--success)">✨ 亮点</div>
          <ul class="point-list">
            <li v-for="(s, i) in ev.strengths" :key="i">{{ s }}</li>
          </ul>
        </div>
        <div class="card col">
          <div class="section-title" style="color: var(--danger)">⚠️ 短板</div>
          <ul class="point-list">
            <li v-for="(s, i) in ev.weaknesses" :key="i">{{ s }}</li>
          </ul>
        </div>
        <div class="card col">
          <div class="section-title" style="color: var(--primary-soft)">💡 改进建议</div>
          <ul class="point-list">
            <li v-for="(s, i) in ev.suggestions" :key="i">{{ s }}</li>
          </ul>
        </div>
      </div>

      <div class="card" v-if="citations.length">
        <div class="section-title">检索依据 / 资料引用</div>
        <div class="citation-list"><div v-for="(c, i) in citations" :key="c.chunk_id || i" class="citation-row"><span class="tag tag-primary">{{ c.source || '资料' }}</span><span class="tag">{{ c.document_type || 'other' }}</span><span v-if="c.page">第 {{ c.page }} 页</span><span v-if="c.line">第 {{ c.line }} 行</span><span>相关度 {{ Math.round((c.score || 0) * 100) }}%</span><p>{{ c.excerpt || c.quote || '' }}</p></div></div>
      </div>
      <div class="card" v-if="routing">
        <div class="section-title">本场模型路由数据</div>
        <div class="growth-grid">
          <span>调用 {{ routing.calls || 0 }} 次</span>
          <span>Token {{ routing.total_tokens || 0 }}</span>
          <span>估算成本 {{ routing.estimated_cost || 0 }}</span>
          <span>节省 {{ routing.saved_cost || 0 }}</span>
          <span>平均延迟 {{ routing.average_latency_ms || 0 }}ms</span>
         </div>
         <p class="text-soft">模型调用：{{ Object.entries(routing.model_calls || {}).map(([model, count]) => `${model}（${count}次）`).join('；') || '暂无记录' }}</p>
        <p class="text-soft">路由原因：{{ Object.entries(routing.route_reasons || {}).map(([reason, count]) => `${reason}（${count}次）`).join('；') || '暂无记录' }}</p>
         <p class="text-soft">对比全程强模型预计节省：{{ routing.full_strong_model_cost ? Math.round((routing.saved_cost / routing.full_strong_model_cost) * 100) : 0 }}%</p>
      </div>
      <div class="card" v-if="growth && growth.previous_session_id">
        <div class="section-title">跨场对比</div>
        <p class="text-soft">总分变化：{{ growth.overall_score_change > 0 ? '+' : '' }}{{ growth.overall_score_change }}</p>
        <div class="growth-grid"><span v-for="(change, name) in growth.dimension_changes" :key="name">{{ name }}：{{ change > 0 ? '+' : '' }}{{ change }}</span></div>
        <p v-if="growth.repeated_weaknesses?.length" class="text-soft">反复短板：{{ growth.repeated_weaknesses.join('、') }}</p>
        <p v-if="growth.coach_dependency" class="text-soft">辅导依赖：{{ growth.coach_dependency.previous }} → {{ growth.coach_dependency.current }} 次</p>
      </div>

      <!-- 总评 -->
      <div class="card">
        <div class="section-title">总体评价</div>
        <p class="summary">{{ ev.summary }}</p>
        <div class="actions mt-4">
          <button class="btn btn-primary" @click="router.push('/chat')">再来一场</button>
          <button class="btn btn-ghost" @click="router.push('/knowledge')">补充资料</button>
          <button class="btn btn-ghost" @click="exportReport">⬇ 导出报告</button>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.report-page {
  max-width: 980px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.empty {
  text-align: center;
  padding: 50px 20px;
}
.empty-icon {
  font-size: 52px;
  margin-bottom: 14px;
  opacity: 0.7;
}
.empty-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 6px;
}
.empty-desc {
  font-size: 14px;
}
.score-card {
  display: flex;
  align-items: center;
  gap: 30px;
}
.score-left {
  flex-shrink: 0;
  text-align: center;
  width: 180px;
}
.score-label {
  color: var(--text-soft);
  font-size: 14px;
  margin-bottom: 6px;
}
.score-num {
  font-size: 64px;
  font-weight: 800;
  line-height: 1;
}
.score-level {
  font-size: 14px;
  font-weight: 600;
  margin-top: 8px;
}
.save-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 12px;
  padding: 4px 12px;
  background: rgba(52, 211, 153, 0.15);
  border: 1px solid rgba(52, 211, 153, 0.3);
  border-radius: var(--radius-pill);
  color: #6ee7b7;
  font-size: 12px;
  font-weight: 500;
}
.save-icon {
  font-size: 12px;
}
.not-saved-badge {
  margin-top: 12px;
  color: var(--warning);
  font-size: 12px;
}
.score-right {
  flex: 1;
}
.section-title {
  font-weight: 700;
  font-size: 16px;
  margin-bottom: 14px;
}
.dim-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.dim-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.dim-name {
  font-weight: 500;
}
.dim-score {
  font-weight: 700;
  font-size: 16px;
}
.dim-bar {
  height: 6px;
  background: var(--bg-hover);
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}
.dim-bar-fill {
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s;
}
.dim-comment {
  line-height: 1.6;
}
.grid-3 {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.point-list {
  list-style: none;
  padding: 0;
}
.point-list li {
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
  line-height: 1.6;
}
.point-list li:last-child {
  border-bottom: none;
}
.summary {
  line-height: 1.8;
  color: var(--text-soft);
}
.citation-list { display: grid; gap: 8px; }
.citation-row { padding: 9px; background: var(--bg); border-radius: var(--radius-sm); color: var(--text-soft); font-size: 12px; }
.citation-row .tag { margin-right: 5px; padding: 2px 7px; }
.citation-row p { margin-top: 5px; line-height: 1.6; }
.growth-grid { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0; }
.growth-grid span { padding: 5px 9px; border: 1px solid var(--border); border-radius: var(--radius-pill); font-size: 12px; }
.actions {
  display: flex;
  gap: 10px;
}

@media (max-width: 768px) {
  .score-card {
    flex-direction: column;
    gap: 16px;
  }
  .score-left {
    width: 100%;
  }
  .score-num {
    font-size: 52px;
  }
  .grid-3 {
    grid-template-columns: 1fr;
  }
}
</style>
