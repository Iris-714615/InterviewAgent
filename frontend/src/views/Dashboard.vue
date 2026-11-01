<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import { deleteSession, getEvaluation, getQuestionsMeta, listSessions } from '../api'
import { useChatStore } from '../stores/chat'
import { ROLE_NAMES, useCatalogStore } from '../stores/catalog'
import { toast } from '../utils/toast'

const router = useRouter()
const chat = useChatStore()
const catalog = useCatalogStore()

const sessions = ref([])
const loadingSessions = ref(true)
const qMeta = ref(null)
const sessionFilter = ref('all')

const features = [
  { icon: 'message', title: '模拟面试', desc: '数十个岗位 + 自定义岗位，技术 / 行为 / HR 三类面试官', path: '/chat', tone: 'primary' },
  { icon: 'library', title: '面试题库', desc: '分方向、分题型、分难度的精选题，练习 + 收藏 + 复盘', path: '/questions', tone: 'info' },
  { icon: 'database', title: '个人资料库', desc: '上传简历与 JD，Agent 结合你的经历精准追问', path: '/knowledge', tone: 'success' },
  { icon: 'chart', title: '评估报告', desc: '多维雷达、亮点短板、改进计划与成长对比', path: '/report', tone: 'warning' }
]

async function loadSessions() {
  loadingSessions.value = true
  try {
    sessions.value = await listSessions()
  } catch (e) {
    sessions.value = []
    toast.error(e.message)
  } finally {
    loadingSessions.value = false
  }
}

const scored = computed(() => sessions.value.filter((s) => s.overall_score != null))
const avgScore = computed(() => scored.value.length
  ? Math.round(scored.value.reduce((a, s) => a + s.overall_score, 0) / scored.value.length)
  : null)
const bestScore = computed(() => scored.value.length ? Math.round(Math.max(...scored.value.map((s) => s.overall_score))) : null)
const delta = computed(() => scored.value.length >= 2
  ? Math.round(scored.value[0].overall_score - scored.value[1].overall_score)
  : null)
const trend = computed(() => scored.value.slice(0, 10).reverse())
const filteredSessions = computed(() => {
  if (sessionFilter.value === 'scored') return sessions.value.filter((s) => s.overall_score != null)
  if (sessionFilter.value === 'pending') return sessions.value.filter((s) => s.overall_score == null)
  return sessions.value
})

const serviceInfo = computed(() => {
  if (chat.serviceStatusError) return { tone: 'danger', label: '服务不可用' }
  if (!chat.serviceStatus) return { tone: 'warning', label: '检查中' }
  if (chat.serviceStatus.demo_mode) return { tone: 'warning', label: '演示模式' }
  return chat.serviceStatus.status === 'ok' ? { tone: 'success', label: '服务正常' } : { tone: 'warning', label: '降级运行' }
})

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 18) return '下午好'
  return '晚上好'
})

function scoreTone(s) {
  if (s == null) return ''
  if (s >= 80) return 'success'
  if (s >= 60) return 'warning'
  return 'danger'
}

function fmtTime(t) {
  if (!t) return ''
  const d = new Date(t)
  const diff = (Date.now() - d) / 1000
  if (diff < 60) return '刚刚'
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`
  const p = (n) => String(n).padStart(2, '0')
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

function nameOf(s) {
  return s.direction_name || catalog.nameOf(s.direction)
}

function startWith(positionId) {
  router.push({ path: '/chat', query: { position: positionId } })
}

const opening = ref('')
async function reviewSession(s) {
  if (opening.value) return
  opening.value = s.session_id
  try {
    await chat.loadHistory(s.session_id, s)
    if (s.overall_score != null) {
      try {
        chat.evaluation = await getEvaluation(s.session_id)
        router.push('/report')
        return
      } catch {
        toast.info('评估结果暂不可用，已为你打开对话记录')
      }
    }
    router.push('/chat')
  } catch (e) {
    toast.error(e.message)
  } finally {
    opening.value = ''
  }
}

async function removeSession(s) {
  if (!window.confirm(`确定删除「${nameOf(s)}」这场面试记录吗？删除后无法恢复。`)) return
  try {
    await deleteSession(s.session_id)
    sessions.value = sessions.value.filter((x) => x.session_id !== s.session_id)
    if (chat.sessionId === s.session_id) chat.reset()
    toast.success('已删除面试记录')
  } catch (e) {
    toast.error(e.message)
  }
}

onMounted(async () => {
  catalog.load()
  chat.loadServiceStatus()
  loadSessions()
  getQuestionsMeta().then((m) => { qMeta.value = m }).catch(() => {})
})
</script>

<template>
  <div class="container dash">
    <!-- Hero -->
    <section class="hero">
      <div class="hero-body">
        <div class="row gap-2 wrap">
          <span class="tag tag-primary"><Icon name="sparkles" :size="12" /> AI 面试官</span>
          <span class="tag" :class="`tag-${serviceInfo.tone}`"><span class="dot" :class="`dot-${serviceInfo.tone}`" /> {{ serviceInfo.label }}</span>
        </div>
        <h1 class="hero-title">{{ greeting }}，今天想练哪个岗位？</h1>
        <p class="hero-desc">选择任意岗位或自定义目标职位，AI 面试官会结合你的简历与 JD 实时追问、即时辅导，并在结束后生成多维评估报告。</p>
        <div class="row wrap gap-3 mt-4">
          <button class="btn btn-gradient btn-lg" @click="router.push('/chat')"><Icon name="play" :size="18" /> 开始模拟面试</button>
          <button class="btn btn-secondary btn-lg" @click="router.push('/questions')"><Icon name="library" :size="18" /> 浏览题库</button>
          <button v-if="chat.hasMessages && chat.sessionId" class="btn btn-ghost btn-lg" @click="router.push('/chat')">
            <Icon name="history" :size="18" /> 继续上次面试
          </button>
        </div>
      </div>
      <div class="hero-side" aria-hidden="true">
        <Icon name="sparkle4" :size="72" class="hero-star s1" />
        <Icon name="sparkle4" :size="22" class="hero-star s2" />
        <Icon name="sparkle4" :size="14" class="hero-star s3" />
        <div class="hero-card card">
          <div class="row gap-2"><Icon name="bot" :size="18" class="text-primary" /><b class="text-sm">面试官</b></div>
          <p class="text-sm text-soft mt-2">请介绍一个你主导的项目，重点说说技术选型的取舍。</p>
          <div class="row gap-2 mt-3">
            <span class="tag tag-success">表达清晰 82</span>
            <span class="tag tag-warning">深度 68</span>
          </div>
        </div>
      </div>
    </section>

    <!-- 统计 -->
    <section class="grid-4 mt-4">
      <div class="card stat">
        <div class="stat-label"><Icon name="message" :size="14" /> 面试场次</div>
        <div class="stat-value">{{ loadingSessions ? '—' : sessions.length }}</div>
        <div class="stat-foot text-dim">已评估 {{ scored.length }} 场</div>
      </div>
      <div class="card stat">
        <div class="stat-label"><Icon name="target" :size="14" /> 平均得分</div>
        <div class="stat-value" :class="avgScore != null && `text-${scoreTone(avgScore)}`">{{ avgScore ?? '—' }}</div>
        <div class="stat-foot text-dim">最高 {{ bestScore ?? '—' }}</div>
      </div>
      <div class="card stat">
        <div class="stat-label"><Icon name="trendUp" :size="14" /> 最近进步</div>
        <div class="stat-value" :class="delta == null ? '' : delta >= 0 ? 'text-success' : 'text-danger'">
          <template v-if="delta == null">—</template>
          <template v-else>{{ delta >= 0 ? '+' : '' }}{{ delta }}</template>
        </div>
        <div class="stat-foot text-dim">对比上一场已评估面试</div>
      </div>
      <div class="card stat">
        <div class="stat-label"><Icon name="library" :size="14" /> 题库练习</div>
        <div class="stat-value">{{ qMeta?.practiced_questions ?? '—' }}<small class="text-dim text-sm"> / {{ qMeta?.total ?? '—' }}</small></div>
        <div class="progress mt-2"><span :style="{ width: qMeta?.total ? `${Math.min(100, qMeta.practiced_questions / qMeta.total * 100)}%` : '0%' }" /></div>
      </div>
    </section>

    <div class="dash-grid mt-4">
      <div class="stack gap-4 main-col">
        <!-- 热门岗位 -->
        <section class="card">
          <div class="row mb-4">
            <div>
              <div class="section-title"><Icon name="zap" :size="16" /> 快速开始</div>
              <p class="text-xs text-dim">热门岗位一键开练，或进入面试页搜索 / 自定义任意岗位</p>
            </div>
            <button class="btn btn-ghost btn-sm ml-auto" @click="router.push('/chat')">全部岗位 <Icon name="chevronRight" :size="14" /></button>
          </div>
          <div v-if="catalog.loading && !catalog.positions.length" class="grid-3">
            <div v-for="i in 6" :key="i" class="skeleton sk-pos" />
          </div>
          <div v-else class="grid-3 pos-grid">
            <button v-for="p in catalog.hotPositions.slice(0, 6)" :key="p.id" class="pos-card" @click="startWith(p.id)">
              <div class="row gap-2">
                <span class="pos-icon"><Icon :name="catalog.categoryMap[p.category]?.icon || 'briefcase'" :size="16" /></span>
                <b class="truncate flex-1">{{ p.name }}</b>
                <Icon name="arrowRight" :size="14" class="pos-go" />
              </div>
              <p class="text-xs text-dim clamp-2 mt-2">{{ p.focus }}</p>
            </button>
          </div>
        </section>

        <!-- 面试记录 -->
        <section class="card">
          <div class="row wrap gap-2 mb-4">
            <div class="section-title"><Icon name="history" :size="16" /> 面试记录</div>
            <div class="segmented ml-auto" role="radiogroup" aria-label="记录筛选">
              <button :class="{ active: sessionFilter === 'all' }" @click="sessionFilter = 'all'">全部</button>
              <button :class="{ active: sessionFilter === 'scored' }" @click="sessionFilter = 'scored'">已评估</button>
              <button :class="{ active: sessionFilter === 'pending' }" @click="sessionFilter = 'pending'">未评估</button>
            </div>
            <button class="btn btn-icon btn-ghost" :disabled="loadingSessions" aria-label="刷新" @click="loadSessions">
              <Icon name="refresh" :size="16" :class="{ spin: loadingSessions }" />
            </button>
          </div>

          <div v-if="loadingSessions && !sessions.length" class="stack gap-2">
            <div v-for="i in 3" :key="i" class="skeleton sk-row" />
          </div>
          <div v-else-if="!filteredSessions.length" class="empty">
            <div class="empty-icon"><Icon name="message" :size="26" /></div>
            <div class="empty-title">{{ sessions.length ? '没有符合条件的记录' : '还没有面试记录' }}</div>
            <div class="empty-desc">完成第一场模拟面试后，这里会展示你的历史与成绩。</div>
            <button v-if="!sessions.length" class="btn btn-primary mt-3" @click="router.push('/chat')"><Icon name="play" :size="14" /> 开始第一场</button>
          </div>
          <div v-else class="stack gap-2">
            <div
              v-for="s in filteredSessions"
              :key="s.session_id"
              class="session"
              role="button"
              tabindex="0"
              @click="reviewSession(s)"
              @keydown.enter.prevent="reviewSession(s)"
            >
              <span class="session-icon"><Icon name="briefcase" :size="16" /></span>
              <div class="flex-1 session-info">
                <div class="row gap-2 wrap">
                  <b class="truncate">{{ nameOf(s) }}</b>
                  <span class="tag">{{ ROLE_NAMES[s.role] || s.role }}</span>
                </div>
                <div class="text-xs text-dim mt-1">{{ fmtTime(s.created_at) }} · {{ s.message_count }} 条对话</div>
              </div>
              <span v-if="s.overall_score != null" class="score" :class="`score-${scoreTone(s.overall_score)}`">{{ Math.round(s.overall_score) }}</span>
              <span v-else class="tag">未评估</span>
              <span v-if="opening === s.session_id" class="spinner" />
              <button class="btn btn-icon btn-ghost btn-sm del" aria-label="删除记录" @click.stop="removeSession(s)"><Icon name="trash" :size="15" /></button>
            </div>
          </div>
        </section>
      </div>

      <aside class="stack gap-4 side-col">
        <!-- 成长趋势 -->
        <section class="card">
          <div class="section-title"><Icon name="trendUp" :size="16" /> 成长趋势</div>
          <div v-if="trend.length < 2" class="text-sm text-dim mt-2">完成至少 2 场评估后展示得分走势。</div>
          <div v-else class="trend mt-3">
            <button
              v-for="s in trend"
              :key="s.session_id"
              class="trend-bar"
              :title="`${nameOf(s)} · ${fmtTime(s.created_at)} · ${Math.round(s.overall_score)} 分`"
              @click="reviewSession(s)"
            >
              <span class="trend-num">{{ Math.round(s.overall_score) }}</span>
              <span class="trend-pill" :class="`bg-${scoreTone(s.overall_score)}`" :style="{ height: `${Math.max(8, s.overall_score)}%` }" />
            </button>
          </div>
        </section>

        <!-- 功能入口 -->
        <section class="card">
          <div class="section-title mb-2"><Icon name="grid" :size="16" /> 功能</div>
          <div class="stack gap-1">
            <button v-for="f in features" :key="f.title" class="feature" @click="router.push(f.path)">
              <span class="f-icon" :class="`f-${f.tone}`"><Icon :name="f.icon" :size="18" /></span>
              <span class="flex-1">
                <b class="text-sm">{{ f.title }}</b>
                <span class="text-xs text-dim f-desc">{{ f.desc }}</span>
              </span>
              <Icon name="chevronRight" :size="14" class="text-dim" />
            </button>
          </div>
        </section>

        <!-- 服务状态 -->
        <section v-if="chat.serviceStatus" class="card">
          <div class="section-title mb-2"><Icon name="server" :size="16" /> 运行状态</div>
          <ul class="status-list text-sm">
            <li><span class="text-dim">模型密钥</span><span :class="chat.serviceStatus.api_key_configured ? 'text-success' : 'text-warning'">{{ chat.serviceStatus.api_key_configured ? '已配置' : '未配置' }}</span></li>
            <li><span class="text-dim">知识文档</span><span>{{ chat.serviceStatus.rag_document_count }}</span></li>
            <li><span class="text-dim">会话存储</span><span :class="chat.serviceStatus.session_writable ? 'text-success' : 'text-danger'">{{ chat.serviceStatus.session_writable ? '可写' : '不可写' }}</span></li>
          </ul>
          <div v-if="chat.serviceStatus.demo_mode" class="alert alert-warning mt-3 text-xs">
            <Icon class="alert-icon" name="info" :size="14" /> 当前为演示模式，配置模型密钥后可获得完整 AI 面试体验。
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.dash { padding-bottom: 48px; }
.hero { position: relative; display: grid; grid-template-columns: 1.4fr 1fr; gap: 24px; padding: 40px; border-radius: var(--radius-lg); background: var(--primary); color: var(--text-on-primary); overflow: hidden; }
.hero-title { margin: 16px 0 12px; font-size: 38px; font-weight: 900; letter-spacing: -.02em; line-height: 1.2; color: var(--text-on-primary); }
.hero-desc { margin: 0; max-width: 560px; color: var(--text-on-primary); line-height: 1.8; font-weight: 500; }
.hero-body :deep(.tag) { background: var(--text-on-primary); color: var(--primary); border-color: var(--text-on-primary); }
.hero-body :deep(.btn-gradient) { background: var(--text-on-primary); color: var(--primary); }
.hero-body :deep(.btn-gradient:hover:not(:disabled)) { opacity: .88; }
.hero-body :deep(.btn-secondary) { background: transparent; color: var(--text-on-primary); border: 2px solid var(--text-on-primary); }
.hero-body :deep(.btn-secondary:hover:not(:disabled)) { background: rgba(128, 128, 128, .2); }
.hero-body :deep(.btn-ghost) { color: var(--text-on-primary); font-weight: 700; }
.hero-body :deep(.btn-ghost:hover:not(:disabled)) { background: rgba(128, 128, 128, .2); }
.hero-side { position: relative; display: flex; align-items: center; justify-content: center; }
.hero-star { position: absolute; color: var(--text-on-primary); }
.hero-star.s1 { right: 8px; top: -6px; }
.hero-star.s2 { right: 0; top: 58px; }
.hero-star.s3 { right: 44px; top: 76px; }
.hero-card { position: relative; width: 100%; max-width: 320px; padding: 18px; background: var(--text-on-primary); color: var(--primary); border: 0; margin-top: 40px; }
.hero-card .text-soft { color: var(--primary); opacity: .8; }
.hero-card .text-primary { color: var(--primary); }@media (max-width: 768px) {
  .hero { grid-template-columns: 1fr; padding: 24px 20px; }
  .hero-title { font-size: 28px; }
  .hero-side { display: none; }
}

.stat-value small { font-weight: 500; }
.dash-grid { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 16px; align-items: start; }

.sk-pos { height: 88px; border-radius: var(--radius-sm); }
.sk-row { height: 64px; border-radius: var(--radius-sm); }
.pos-card { display: block; width: 100%; padding: 14px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-soft); color: var(--text); font: inherit; text-align: left; cursor: pointer; transition: border-color var(--dur) var(--ease), transform var(--dur) var(--ease), background var(--dur) var(--ease); }
.pos-card:hover { border-color: var(--primary-border); background: var(--bg-hover); transform: translateY(-2px); }
.pos-card:focus-visible { outline: 2px solid var(--primary-border); }
.pos-icon { width: 28px; height: 28px; border-radius: var(--radius-xs); display: grid; place-items: center; background: var(--primary-bg); color: var(--primary); flex: none; }
.pos-go { color: var(--text-dim); transition: transform var(--dur) var(--ease), color var(--dur) var(--ease); }
.pos-card:hover .pos-go { color: var(--primary); transform: translateX(3px); }
.pos-card p { margin-bottom: 0; }

.session { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-soft); cursor: pointer; transition: border-color var(--dur) var(--ease), background var(--dur) var(--ease); }
.session:hover { border-color: var(--primary-border); background: var(--bg-hover); }
.session:focus-visible { outline: 2px solid var(--primary-border); }
.session-icon { width: 34px; height: 34px; border-radius: var(--radius-xs); display: grid; place-items: center; background: var(--bg-card); color: var(--text-soft); border: 1px solid var(--border); flex: none; }
.session-info { min-width: 0; }
.score { min-width: 44px; text-align: center; font-weight: 800; font-size: 16px; padding: 2px 8px; border-radius: var(--radius-pill); }
.score-success { color: var(--success); background: var(--success-bg); }
.score-warning { color: var(--warning); background: var(--warning-bg); }
.score-danger { color: var(--danger); background: var(--danger-bg); }
.del { color: var(--text-dim); opacity: 0; transition: opacity var(--dur) var(--ease); }
.session:hover .del, .del:focus-visible { opacity: 1; }
.del:hover { color: var(--danger); }

.trend { display: flex; align-items: flex-end; gap: 8px; height: 140px; }
.trend-bar { flex: 1; height: 100%; display: flex; flex-direction: column; justify-content: flex-end; align-items: center; gap: 4px; background: none; border: 0; padding: 0; cursor: pointer; }
.trend-num { font-size: 11px; font-weight: 700; color: var(--text-soft); }
.trend-pill { width: 100%; max-width: 22px; border-radius: 6px 6px 2px 2px; transition: height .4s var(--ease), opacity var(--dur); opacity: .85; }
.trend-bar:hover .trend-pill { opacity: 1; }
.bg-success { background: var(--success); }
.bg-warning { background: var(--warning); }
.bg-danger { background: var(--danger); }

.feature { display: flex; align-items: center; gap: 12px; width: 100%; padding: 10px; border: 0; border-radius: var(--radius-sm); background: none; color: var(--text); font: inherit; text-align: left; cursor: pointer; transition: background var(--dur) var(--ease); }
.feature:hover { background: var(--bg-hover); }
.f-desc { display: block; margin-top: 2px; line-height: 1.5; }
.f-icon { width: 36px; height: 36px; border-radius: var(--radius-sm); display: grid; place-items: center; flex: none; }
.f-primary { background: var(--primary-bg); color: var(--primary); }
.f-info { background: var(--info-bg); color: var(--info); }
.f-success { background: var(--success-bg); color: var(--success); }
.f-warning { background: var(--warning-bg); color: var(--warning); }

.status-list { list-style: none; margin: 0; padding: 0; display: grid; gap: 8px; }
.status-list li { display: flex; justify-content: space-between; }
.spin { animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

@media (max-width: 1100px) {
  .dash-grid { grid-template-columns: 1fr; }
  .hero { grid-template-columns: 1fr; }
  .hero-side { display: none; }
}
@media (max-width: 768px) {
  .hero { padding: 24px; }
  .hero-title { font-size: 22px; }
  .del { opacity: 1; }
}
</style>
