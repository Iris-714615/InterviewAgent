<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { listSessions, getEvaluation, getGrowthSummary, getRoutingMetrics } from '../api'
import { useChatStore } from '../stores/chat'

const router = useRouter()
const chat = useChatStore()

const features = [
  { icon: '💬', title: '模拟面试', desc: '多方向、多角色面试官,一对一真实演练', path: '/chat' },
  { icon: '📚', title: '个人资料库', desc: '上传简历/面经/笔记,Agent 基于你的经历提问', path: '/knowledge' },
  { icon: '🎓', title: '实时辅导', desc: '面试中随时求助教练,给参考答案与思路', path: '/chat' },
  { icon: '📊', title: '评估报告', desc: '雷达图打分、弱点分析、改进建议', path: '/report' }
]

const directions = [
  { name: 'AI 大模型应用工程师', tag: 'RAG · Agent · Prompt', color: 'var(--primary)' },
  { name: 'AI 应用开发工程师', tag: 'API · 工程化 · 流式', color: 'var(--success)' },
  { name: 'AI 产品经理', tag: '落地 · 商业 · 方法论', color: 'var(--warning)' }
]

const steps = [
  { n: 1, t: '上传资料', d: '把简历、项目、面经喂给 Agent' },
  { n: 2, t: '模拟面试', d: '选择方向与角色,开始一对一演练' },
  { n: 3, t: '实时辅导', d: '卡壳时求助教练,给参考答案' },
  { n: 4, t: '评估迭代', d: '查看雷达图,针对短板反复练' }
]

// 方向/角色中文映射
const dirLabel = { ai_app_engineer: 'AI大模型应用', ai_dev_engineer: 'AI应用开发', ai_product_manager: 'AI产品经理' }
const roleLabel = { technical: '技术面', hr: 'HR面', behavioral: '行为面' }

// 面试记录历史
const sessions = ref([])
const loadingSessions = ref(false)
const growth = ref(null)
const routing = ref(null)

async function loadSessions() {
  loadingSessions.value = true
  try {
    sessions.value = await listSessions()
  } catch (e) {
    sessions.value = []
  } finally {
    loadingSessions.value = false
  }
}

// 已评估的会话(用于得分趋势)
const scoredSessions = () => sessions.value.filter((s) => s.overall_score != null && (!s.evaluation_status || s.evaluation_status === 'completed'))
const serviceLabel = computed(() => {
  if (chat.serviceStatusError) return '不可用'
  if (!chat.serviceStatus) return '检查中'
  if (chat.serviceStatus.demo_mode) return '演示模式'
  return chat.serviceStatus.status === 'ok' ? '正常' : '降级'
})

// ============ 成长概览计算属性 ============
const avgScore = computed(() => {
  const scored = scoredSessions()
  if (scored.length === 0) return '-'
  const avg = scored.reduce((sum, s) => sum + s.overall_score, 0) / scored.length
  return avg.toFixed(0)
})

const avgScoreColor = computed(() => {
  const avg = parseFloat(avgScore.value)
  if (isNaN(avg)) return 'var(--text-soft)'
  return scoreColor(avg)
})

const maxScore = computed(() => {
  const scored = scoredSessions()
  if (scored.length === 0) return '-'
  return Math.max(...scored.map((s) => s.overall_score)).toFixed(0)
})

const progressDelta = computed(() => {
  const scored = scoredSessions()
  if (scored.length < 2) return '-'
  const latest = scored[0].overall_score
  const prev = scored[1].overall_score
  return Math.abs(latest - prev).toFixed(0)
})

const progressSign = computed(() => {
  const scored = scoredSessions()
  if (scored.length < 2) return ''
  const latest = scored[0].overall_score
  const prev = scored[1].overall_score
  return latest >= prev ? '+' : '-'
})

const progressColor = computed(() => {
  const scored = scoredSessions()
  if (scored.length < 2) return 'var(--text-soft)'
  const latest = scored[0].overall_score
  const prev = scored[1].overall_score
  return latest >= prev ? '#6ee7b7' : '#fca5a5'
})

function scoreColor(s) {
  if (s == null) return 'var(--text-soft)'
  if (s >= 80) return 'var(--success)'
  if (s >= 60) return 'var(--warning)'
  return 'var(--danger)'
}

function fmtTime(t) {
  if (!t) return ''
  const d = new Date(t)
  const now = new Date()
  const diff = (now - d) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)}分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}小时前`
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${mm}-${dd} ${hh}:${mi}`
}

// 查看历史会话(已评估的直接跳报告,未评估的跳对话)
async function reviewSession(s) {
  await chat.loadHistory(s.session_id, s)
  if (s.overall_score != null) {
    // 已评估:加载评估结果并跳转报告页
    try {
      const evaluation = await getEvaluation(s.session_id)
      chat.evaluation = evaluation
      router.push('/report')
    } catch (e) {
      // 获取评估失败,跳对话页
      router.push('/chat')
    }
  } else {
    router.push('/chat')
  }
}

onMounted(() => {
  loadSessions()
  chat.loadServiceStatus()
})
</script>

<template>
  <div class="dashboard">
    <div class="hero card">
      <h1 class="hero-title">你的 AI 面试私教</h1>
      <p class="hero-desc">
        基于你的个人资料库,一对一模拟面试 + 实时辅导 + 评估反馈,<br />
        帮你迭代拿到高薪 offer。
      </p>
      <div class="hero-actions">
        <button class="btn btn-primary" @click="router.push('/chat')">开始模拟面试 →</button>
        <button class="btn btn-ghost" @click="router.push('/knowledge')">先上传资料</button>
      </div>
    </div>

    <div class="card service-card" :class="`service-${chat.serviceStatus?.status || 'loading'}`">
      <div>
        <strong>服务状态：{{ serviceLabel }}</strong>
        <span v-if="chat.serviceStatusError" class="service-error">{{ chat.serviceStatusError }}</span>
      </div>
      <div v-if="chat.serviceStatus" class="service-details">
        <span>模型密钥：{{ chat.serviceStatus.api_key_configured ? '已配置' : '未配置' }}</span>
        <span>RAG 文档：{{ chat.serviceStatus.rag_document_count }}</span>
        <span>会话存储：{{ chat.serviceStatus.session_writable ? '可写' : '不可写' }}</span>
        <span v-if="chat.serviceStatus.demo_mode">DEMO 已启用</span>
      </div>
    </div>

    <div class="grid">
      <div v-for="f in features" :key="f.title" class="card feature" @click="router.push(f.path)">
        <div class="f-icon">{{ f.icon }}</div>
        <div class="f-title">{{ f.title }}</div>
        <div class="f-desc">{{ f.desc }}</div>
      </div>
    </div>

    <!-- 面试记录历史 -->
    <div class="card">
      <div class="section-head">
        <div class="section-title">面试记录</div>
        <button class="btn btn-ghost btn-sm" @click="loadSessions" :disabled="loadingSessions">
          {{ loadingSessions ? '刷新中…' : '↻ 刷新' }}
        </button>
      </div>

      <!-- 成长概览 -->
      <div v-if="scoredSessions().length >= 1" class="stats-grid">
        <div class="stat-item">
          <div class="stat-value">{{ sessions.length }}</div>
          <div class="stat-label">总场次</div>
        </div>
        <div class="stat-item">
          <div class="stat-value">{{ scoredSessions().length }}</div>
          <div class="stat-label">已评估</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" :style="{ color: avgScoreColor }">{{ avgScore }}</div>
          <div class="stat-label">平均分</div>
        </div>
        <div class="stat-item">
          <div class="stat-value" :style="{ color: '#6ee7b7' }">{{ maxScore }}</div>
          <div class="stat-label">最高分</div>
        </div>
        <div class="stat-item" v-if="scoredSessions().length >= 2">
          <div class="stat-value" :style="{ color: progressColor }">{{ progressSign }}{{ progressDelta }}</div>
          <div class="stat-label">进步幅度</div>
        </div>
      </div>

      <!-- 得分趋势 -->
      <div v-if="scoredSessions().length >= 2" class="trend">
        <span class="trend-label text-soft text-sm">进步轨迹</span>
        <div class="trend-bars">
          <div
            v-for="(s, i) in scoredSessions().slice().reverse()"
            :key="s.session_id"
            class="trend-bar"
            :title="`${fmtTime(s.created_at)}:${s.overall_score.toFixed(0)}分`"
            @click="reviewSession(s)"
          >
            <div class="trend-num" :style="{ color: scoreColor(s.overall_score) }">{{ s.overall_score.toFixed(0) }}</div>
            <div class="trend-pill" :style="{ height: Math.max(8, s.overall_score * 0.5) + 'px', background: scoreColor(s.overall_score) }"></div>
          </div>
        </div>
      </div>

      <!-- 记录列表 -->
      <div v-if="sessions.length" class="session-list">
        <div v-for="s in sessions" :key="s.session_id" class="session-item" @click="reviewSession(s)">
          <div class="session-tags">
            <span class="tag tag-primary">{{ dirLabel[s.direction] || s.direction }}</span>
            <span class="tag">{{ roleLabel[s.role] || s.role }}</span>
          </div>
          <div class="session-meta text-soft text-sm">
            {{ fmtTime(s.created_at) }} · {{ s.message_count }} 条对话
          </div>
          <div class="session-score">
            <span v-if="s.overall_score != null" class="score-pill" :style="{ color: scoreColor(s.overall_score), borderColor: scoreColor(s.overall_score) }">
              {{ s.overall_score.toFixed(0) }} 分
            </span>
            <span v-else class="score-pill unscored">未评估</span>
          </div>
          <span class="session-go">回顾 →</span>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!loadingSessions" class="empty-hint text-soft text-sm">
        还没有面试记录,去开始第一场模拟面试吧
      </div>
    </div>

    <div class="card">
      <div class="section-title">支持的面试方向</div>
      <div class="dir-list">
        <div v-for="d in directions" :key="d.name" class="dir-item">
          <span class="dir-dot" :style="{ background: d.color }"></span>
          <span class="dir-name">{{ d.name }}</span>
          <span class="tag">{{ d.tag }}</span>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="section-title">使用流程</div>
      <div class="steps">
        <div v-for="s in steps" :key="s.n" class="step">
          <div class="step-n">{{ s.n }}</div>
          <div>
            <div class="step-t">{{ s.t }}</div>
            <div class="step-d text-soft text-sm">{{ s.d }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  max-width: 980px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.hero {
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.18), rgba(139, 92, 246, 0.1));
  border-color: rgba(99, 102, 241, 0.3);
  position: relative;
  overflow: hidden;
}
.hero::before {
  content: '';
  position: absolute;
  top: -50%;
  right: -10%;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(217, 70, 239, 0.12), transparent 70%);
  pointer-events: none;
}
.hero-title {
  font-size: 28px;
  font-weight: 800;
  margin-bottom: 10px;
  letter-spacing: -0.02em;
  background: var(--gradient-primary);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.hero-desc {
  color: #c7d2fe;
  font-size: 15px;
  line-height: 1.8;
  margin-bottom: 20px;
}
.hero-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.service-card { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 14px 18px; }
.service-ok { border-color: rgba(52, 211, 153, .35); }
.service-degraded { border-color: rgba(245, 158, 11, .45); }
.service-details { display: flex; gap: 14px; flex-wrap: wrap; color: var(--text-soft); font-size: 13px; }
.service-error { margin-left: 10px; color: var(--danger); font-size: 12px; }
.grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 14px;
}
.feature {
  cursor: pointer;
  transition: transform 0.15s, border-color 0.15s;
}
.feature:hover {
  transform: translateY(-2px);
  border-color: var(--primary);
}
.f-icon {
  font-size: 28px;
  margin-bottom: 10px;
}
.f-title {
  font-weight: 600;
  margin-bottom: 4px;
}
.f-desc {
  color: var(--text-soft);
  font-size: 13px;
  line-height: 1.5;
}
.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.section-head .section-title {
  margin-bottom: 0;
}
.section-title {
  font-weight: 700;
  font-size: 16px;
  margin-bottom: 16px;
}
.btn-sm {
  padding: 5px 12px;
  font-size: 13px;
}

/* 成长概览 */
.stats-grid {
  display: flex;
  gap: 16px;
  margin-bottom: 18px;
  padding: 16px;
  background: var(--bg);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  flex-wrap: wrap;
}
.stat-item {
  flex: 1;
  min-width: 80px;
  text-align: center;
}
.stat-value {
  font-size: 28px;
  font-weight: 800;
  line-height: 1.2;
}
.stat-label {
  font-size: 12px;
  color: var(--text-soft);
  margin-top: 4px;
}

/* 得分趋势 */
.trend {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 18px;
  padding: 12px 14px;
  background: var(--bg);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
}
.trend-label {
  flex-shrink: 0;
}
.trend-bars {
  display: flex;
  align-items: flex-end;
  gap: 10px;
  flex: 1;
  overflow-x: auto;
}
.trend-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  min-width: 36px;
}
.trend-num {
  font-size: 12px;
  font-weight: 700;
}
.trend-pill {
  width: 24px;
  border-radius: 4px 4px 2px 2px;
  transition: height 0.3s;
  min-height: 8px;
}

/* 记录列表 */
.session-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.session-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.session-item:hover {
  border-color: var(--primary);
  background: var(--bg-hover);
}
.session-tags {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
.session-meta {
  flex: 1;
}
.session-score {
  flex-shrink: 0;
}
.score-pill {
  font-size: 13px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 12px;
  border: 1px solid;
}
.score-pill.unscored {
  color: var(--text-soft);
  border-color: var(--border);
  font-weight: 500;
}
.session-go {
  flex-shrink: 0;
  font-size: 13px;
  color: var(--text-soft);
}
.empty-hint {
  text-align: center;
  padding: 24px 0;
}

.dir-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.dir-item {
  display: flex;
  align-items: center;
  gap: 10px;
}
.dir-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.dir-name {
  font-weight: 500;
}
.steps {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}
.step {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.step-n {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  flex-shrink: 0;
}
.step-t {
  font-weight: 600;
  margin-bottom: 2px;
}

@media (max-width: 768px) {
  .service-card {
    align-items: flex-start;
    flex-direction: column;
  }
  .grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .steps {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .hero-title {
    font-size: 22px;
  }
  .hero-desc br {
    display: none;
  }
  .session-item {
    flex-wrap: wrap;
    gap: 8px;
  }
  .session-meta {
    width: 100%;
    order: 3;
  }
}
</style>
