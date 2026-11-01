<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import ChatMessage from '../components/ChatMessage.vue'
import PositionPicker from '../components/PositionPicker.vue'
import { useChatStore } from '../stores/chat'
import { ROLE_NAMES, useCatalogStore } from '../stores/catalog'
import { useVoiceInput } from '../composables/useVoiceInput'
import { useSystemAudio } from '../composables/useSystemAudio'
import { speakText, stopSpeech } from '../utils/speech'
import { toast } from '../utils/toast'

const route = useRoute()
const router = useRouter()
const chat = useChatStore()
const catalog = useCatalogStore()

const input = ref('')
const scrollEl = ref(null)
const inputEl = ref(null)
const starting = ref(false)
const panelOpen = ref(typeof window !== 'undefined' ? window.innerWidth > 1100 : true)
const pendingQuestion = ref('')

// ============ 配置向导 ============
const draft = ref({
  direction: chat.direction || '',
  role: chat.role || 'technical',
  positionDescription: chat.positionDescription || ''
})
const inSession = computed(() => Boolean(chat.sessionId) || chat.messages.length > 0)
const draftName = computed(() => catalog.nameOf(draft.value.direction))
const canStart = computed(() => Boolean(draft.value.direction) && !starting.value)

async function startInterview() {
  if (!canStart.value) return
  starting.value = true
  stopAutoTTS()
  chat.reset()
  chat.configure({
    direction: draft.value.direction,
    directionName: draftName.value,
    role: draft.value.role,
    positionDescription: draft.value.positionDescription.trim()
  })
  try {
    await chat.startSession()
  } catch {
    chat.runtimeMode = 'guided'
    toast.info('服务连接较慢，已切换到基础练习模式')
  }
  starting.value = false
  const opener = pendingQuestion.value
    ? `开始面试。请先考察这道题：${pendingQuestion.value}`
    : '开始面试'
  pendingQuestion.value = ''
  await chat.send(opener)
  focusInput()
}

// ============ 面试中 ============
const roleName = computed(() => ROLE_NAMES[chat.role] || chat.role)
const sessionTitle = computed(() => chat.directionName || catalog.nameOf(chat.direction))
const canSend = computed(() => Boolean(input.value.trim()) && !chat.streaming)

const modeInfo = computed(() => ({
  normal: { text: '服务正常', dot: 'success' },
  ok: { text: '服务正常', dot: 'success' },
  degraded: { text: '基础练习', dot: 'warning' },
  guided: { text: '基础练习', dot: 'warning' },
  demo: { text: '演示模式', dot: 'warning' }
}[chat.runtimeMode] || { text: chat.runtimeMode, dot: '' }))

const ragLabel = computed(() => ({
  used: '已引用资料', empty: '资料无匹配', disabled: '资料检索关闭', unconfigured: '未上传资料',
  error: '资料暂不可用', fallback: '资料暂不可用', keyword: '本地检索', pending: '检索中'
}[chat.rag?.status] || '等待检索'))

const profileDimensions = computed(() => Object.entries(chat.profile?.dimensions || {}).map(([name, value]) => ({
  name,
  score: Math.round(Number(value?.score || 0)),
  evidence: value?.evidence || ''
})))
const profileConfidence = computed(() => {
  const v = chat.profile?.confidence
  return typeof v === 'number' ? Math.round(v * 100) : null
})

function scoreTone(score) {
  if (score >= 80) return { text: '强项', cls: 'success' }
  if (score >= 60) return { text: '稳定', cls: 'info' }
  return { text: '待提升', cls: 'warning' }
}

const quickPrompts = computed(() => chat.coachMode
  ? ['这道题的参考答案是什么？', '帮我用 STAR 法则重组刚才的回答', '面试官最想听到什么？']
  : ['请换一道题', '能再具体说明一下问题吗？', '我想先思考一下思路'])

async function scrollToBottom(force = false) {
  await nextTick()
  const el = scrollEl.value
  if (!el) return
  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 160
  if (force || nearBottom) el.scrollTop = el.scrollHeight
}

function focusInput() {
  nextTick(() => inputEl.value?.focus())
}

async function handleSend(text) {
  const msg = (typeof text === 'string' ? text : input.value).trim()
  if (!msg || chat.streaming) return
  stopAutoTTS()
  voice.stop()
  input.value = ''
  autoGrow()
  scrollToBottom(true)
  await chat.send(msg)
  scrollToBottom()
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    handleSend()
  }
}

function autoGrow() {
  nextTick(() => {
    const el = inputEl.value
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`
  })
}

function newInterview() {
  if (chat.streaming) return
  if (chat.hasMessages && !window.confirm('开始新面试后，当前对话仍保存在面试记录中。确认继续？')) return
  stopAutoTTS()
  audio.stop()
  draft.value = { direction: chat.direction, role: chat.role, positionDescription: chat.positionDescription }
  chat.reset()
}

async function finishAndEvaluate() {
  if (!chat.hasMessages || chat.evaluating) return
  if (chat.answerCount < 2 && !window.confirm('目前作答较少，报告的参考价值有限。仍要结束并生成报告吗？')) return
  stopAutoTTS()
  audio.stop()
  await chat.runEvaluation()
  router.push('/report')
}

// ============ 导出 Markdown ============
function pad(n) { return String(n).padStart(2, '0') }
function stamp(d, sep = false) {
  const date = `${d.getFullYear()}${sep ? '-' : ''}${pad(d.getMonth() + 1)}${sep ? '-' : ''}${pad(d.getDate())}`
  const time = `${pad(d.getHours())}${sep ? ':' : ''}${pad(d.getMinutes())}${sep ? ':' : ''}${pad(d.getSeconds())}`
  return sep ? `${date} ${time}` : `${date}_${time}`
}

function exportChat() {
  if (!chat.messages.length) return
  const now = new Date()
  const lines = [
    '# 模拟面试记录', '',
    `- 岗位：${sessionTitle.value}`,
    `- 轮次：${roleName.value}`,
    `- 时间：${stamp(now, true)}`,
    `- 消息数：${chat.messages.length}`
  ]
  if (chat.positionDescription) lines.push(`- 岗位描述：${chat.positionDescription.replace(/\n/g, ' ')}`)
  lines.push('', '---', '')
  for (const m of chat.messages) {
    const speaker = m.channel === 'coach'
      ? (m.role === 'user' ? '向教练提问' : '教练提示')
      : (m.role === 'user' ? '我' : '面试官')
    lines.push(`### ${speaker}`, m.content || '', '')
  }
  const url = URL.createObjectURL(new Blob([lines.join('\n')], { type: 'text/markdown' }))
  const a = document.createElement('a')
  a.href = url
  a.download = `面试记录_${stamp(now)}.md`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
  toast.success('面试记录已导出')
}

// ============ 语音输入 / 系统音频 ============
const voice = useVoiceInput((text) => {
  input.value = text
  autoGrow()
})
const audio = useSystemAudio()

function toggleVoice() {
  voice.toggle(input.value.trim())
}

function useAsrAsInput() {
  const text = audio.asrText.value.trim()
  if (!text) return
  input.value = input.value.trim() ? `${input.value.trim()}\n${text}` : text
  audio.asrText.value = ''
  autoGrow()
  focusInput()
}

// ============ 自动朗读面试官回复（按句入队，边流式边朗读） ============
const autoTTS = ref(false)
const ttsBusy = ref(false)
let autoSpeechController = null
let spokenLength = 0
let speakingMessageId = null
let speechQueue = Promise.resolve()

function stopAutoTTS() {
  autoSpeechController?.abort()
  autoSpeechController = null
  stopSpeech()
  spokenLength = 0
  speakingMessageId = null
  speechQueue = Promise.resolve()
  ttsBusy.value = false
}

function queueSpeech(text) {
  if (!text.trim()) return
  const controller = autoSpeechController
  ttsBusy.value = true
  speechQueue = speechQueue.then(async () => {
    if (controller?.signal.aborted) return
    try { await speakText(text, controller?.signal) } catch { /* 文字仍保留在对话中 */ }
  }).finally(() => { if (controller === autoSpeechController) ttsBusy.value = false })
}

watch(() => chat.messages.at(-1)?.content || '', (content) => {
  const last = chat.messages.at(-1)
  if (!autoTTS.value || !last || last.role !== 'assistant' || last.channel !== 'interview') return
  if (speakingMessageId !== last.message_id) {
    stopAutoTTS()
    speakingMessageId = last.message_id
    autoSpeechController = new AbortController()
  }
  let rest = content.slice(spokenLength)
  let match = rest.match(/^[\s\S]*?[。！？!?\n]/)
  while (match) {
    spokenLength += match[0].length
    queueSpeech(match[0])
    rest = content.slice(spokenLength)
    match = rest.match(/^[\s\S]*?[。！？!?\n]/)
  }
})

watch(() => chat.streaming, (streaming, prev) => {
  if (!prev || streaming || !autoTTS.value) return
  const last = chat.messages.at(-1)
  if (last?.role === 'assistant' && last.channel === 'interview') {
    if (!autoSpeechController) autoSpeechController = new AbortController()
    queueSpeech(last.content.slice(spokenLength))
    spokenLength = last.content.length
  }
})
watch(autoTTS, (on) => { if (!on) stopAutoTTS() })

watch(() => chat.messages.length, () => scrollToBottom(true))
watch(() => chat.messages.at(-1)?.content, () => { if (chat.streaming) scrollToBottom() })

// ============ 生命周期 ============
function applyRouteQuery() {
  const { position, role, question } = route.query
  if (!position && !question) return false
  if (typeof position === 'string' && position) draft.value.direction = position
  if (typeof role === 'string' && ROLE_NAMES[role]) draft.value.role = role
  if (typeof question === 'string' && question) pendingQuestion.value = question.slice(0, 300)
  router.replace({ path: '/chat' })
  return true
}

onMounted(async () => {
  catalog.load()
  chat.loadServiceStatus()
  const fromQuery = applyRouteQuery()
  if (fromQuery) {
    // 从题库/首页带参进入：开新面试配置
    if (inSession.value) {
      chat.reset()
    }
    return
  }
  if (chat.sessionId) {
    scrollToBottom(true)
    return
  }
  const ok = await chat.restoreFromLocal()
  if (ok) {
    toast.info(`已恢复上次面试（${chat.messages.length} 条消息）`)
    scrollToBottom(true)
  }
})

onBeforeUnmount(() => {
  stopAutoTTS()
})
</script>

<template>
  <!-- ================= 配置向导 ================= -->
  <div v-if="!inSession" class="setup">
    <div class="container-narrow">
      <header class="page-head setup-head">
        <div>
          <span class="eyebrow"><Icon name="sparkles" :size="14" /> AI 模拟面试</span>
          <h1 class="page-title">配置你的专属面试</h1>
          <p class="page-sub">选择岗位与轮次，AI 面试官会结合岗位要求、题库与你的简历资料动态追问</p>
        </div>
      </header>

      <div v-if="pendingQuestion" class="alert alert-info mb-4">
        <Icon name="bulb" :size="16" class="alert-icon" />
        <div class="flex-1">
          <div class="text-sm"><b>已选定开场题：</b>{{ pendingQuestion }}</div>
        </div>
        <button type="button" class="btn btn-sm btn-ghost" aria-label="移除开场题" @click="pendingQuestion = ''">
          <Icon name="x" :size="14" />
        </button>
      </div>

      <div class="card setup-card">
        <PositionPicker
          v-model:direction="draft.direction"
          v-model:role="draft.role"
          v-model:position-description="draft.positionDescription"
        />
      </div>

      <div class="setup-foot">
        <div class="summary">
          <template v-if="draft.direction">
            <span class="text-dim text-sm">即将开始</span>
            <span class="tag tag-primary"><Icon name="briefcase" :size="12" /> {{ draftName }}</span>
            <span class="tag"><Icon name="layers" :size="12" /> {{ ROLE_NAMES[draft.role] }}</span>
          </template>
          <span v-else class="text-dim text-sm">请先选择或输入一个目标岗位</span>
        </div>
        <button type="button" class="btn btn-gradient btn-lg" :disabled="!canStart" @click="startInterview">
          <span v-if="starting" class="spinner" />
          <Icon v-else name="play" :size="16" />
          {{ starting ? '正在准备面试官…' : '开始面试' }}
        </button>
      </div>
    </div>
  </div>

  <!-- ================= 面试中 ================= -->
  <div v-else class="room" :class="{ 'panel-open': panelOpen }">
    <section class="main">
      <header class="topbar">
        <div class="topbar-info">
          <div class="title-row">
            <h1 class="room-title truncate">{{ sessionTitle }}</h1>
            <span class="tag">{{ roleName }}</span>
            <span v-if="chat.coachMode" class="tag tag-coach"><Icon name="graduation" :size="12" /> 教练模式</span>
          </div>
          <div class="status-row">
            <span class="status"><span class="dot" :class="modeInfo.dot ? `dot-${modeInfo.dot}` : ''" />{{ modeInfo.text }}</span>
            <span class="status"><Icon name="database" :size="12" />{{ ragLabel }}</span>
            <span class="status"><Icon name="message" :size="12" />已作答 {{ chat.answerCount }} 轮</span>
          </div>
        </div>
        <div class="topbar-actions">
          <button
            type="button"
            class="btn btn-sm btn-coach"
            :class="{ active: chat.coachMode }"
            :aria-pressed="chat.coachMode"
            title="教练模式：获取答题思路与参考答案，不计入面试评估"
            @click="chat.toggleCoachMode()"
          >
            <Icon name="graduation" :size="15" /> <span class="hide-sm">教练</span>
          </button>
          <button type="button" class="btn btn-sm btn-ghost btn-icon" title="导出 Markdown" aria-label="导出面试记录" :disabled="!chat.messages.length" @click="exportChat">
            <Icon name="download" :size="16" />
          </button>
          <button type="button" class="btn btn-sm btn-ghost btn-icon" title="新面试" aria-label="开始新面试" :disabled="chat.streaming" @click="newInterview">
            <Icon name="plus" :size="16" />
          </button>
          <button type="button" class="btn btn-sm btn-ghost btn-icon" :class="{ active: panelOpen }" title="实时画像" aria-label="切换实时画像面板" @click="panelOpen = !panelOpen">
            <Icon name="chart" :size="16" />
          </button>
          <button type="button" class="btn btn-sm btn-primary" :disabled="!chat.hasMessages || chat.evaluating || chat.streaming" @click="finishAndEvaluate">
            <span v-if="chat.evaluating" class="spinner" />
            <Icon v-else name="flag" :size="15" />
            <span class="hide-sm">{{ chat.evaluating ? '生成报告中…' : '结束并评估' }}</span>
          </button>
        </div>
      </header>

      <div ref="scrollEl" class="messages" aria-live="polite">
        <div class="messages-inner">
          <div v-if="chat.restored" class="restored-tip">
            <Icon name="history" :size="13" /> 已从面试记录恢复，可继续作答
          </div>
          <ChatMessage
            v-for="m in chat.messages"
            :key="m.message_id"
            :role="m.role"
            :content="m.content"
            :coach="m.channel === 'coach'"
            :model="m.model"
            :route-reason="m.route_reason"
            :retrieval="m.retrieval"
            :fallback="m.fallback"
            :streaming="chat.streaming && m === chat.messages.at(-1)"
          />
        </div>
      </div>

      <footer class="composer-wrap">
        <!-- 系统音频字幕 -->
        <transition name="fade">
          <div v-if="audio.listening.value || audio.asrText.value" class="asr-panel">
            <div class="asr-head">
              <span class="row gap-2 text-xs">
                <span class="dot" :class="audio.listening.value ? 'dot-danger dot-pulse' : ''" />
                {{ audio.listening.value ? '正在识别面试官声音' : '识别已暂停' }}
                <span v-if="audio.asrBusy.value" class="spinner spinner-xs" />
              </span>
              <span class="row gap-1 ml-auto">
                <button type="button" class="btn btn-sm btn-ghost" :disabled="!audio.asrText.value" @click="useAsrAsInput">
                  <Icon name="arrowUp" :size="13" /> 填入输入框
                </button>
                <button type="button" class="btn btn-sm btn-ghost" :disabled="!audio.asrText.value" @click="audio.asrText.value = ''">
                  清空
                </button>
              </span>
            </div>
            <div class="asr-text" :class="{ placeholder: !audio.asrText.value }">
              {{ audio.asrText.value || '等待识别结果…' }}
            </div>
          </div>
        </transition>

        <div class="quick">
          <button v-for="q in quickPrompts" :key="q" type="button" class="chip chip-sm" :disabled="chat.streaming" @click="handleSend(q)">
            {{ q }}
          </button>
        </div>

        <div class="composer" :class="{ coach: chat.coachMode, focusable: true }">
          <textarea
            ref="inputEl"
            v-model="input"
            class="composer-input"
            rows="1"
            :placeholder="chat.coachMode ? '向 AI 教练提问，获取答题思路或参考答案…' : '输入你的回答，Enter 发送，Shift + Enter 换行'"
            aria-label="输入回答"
            @keydown="onKeydown"
            @input="autoGrow"
          />
          <div class="composer-bar">
            <div class="row gap-1">
              <button
                v-if="voice.supported"
                type="button"
                class="tool"
                :class="{ on: voice.recognizing.value }"
                :title="voice.recognizing.value ? '停止语音输入' : '语音输入'"
                :aria-pressed="voice.recognizing.value"
                @click="toggleVoice"
              >
                <Icon :name="voice.recognizing.value ? 'micOff' : 'mic'" :size="17" />
              </button>
              <button
                type="button"
                class="tool"
                :class="{ on: audio.listening.value }"
                :title="audio.listening.value ? '停止监听系统音频' : '监听会议软件中的面试官声音'"
                :aria-pressed="audio.listening.value"
                @click="audio.toggle()"
              >
                <Icon name="monitor" :size="17" />
              </button>
              <span class="sep" />
              <button type="button" class="tool-switch" :aria-pressed="autoTTS" title="自动朗读面试官回复" @click="autoTTS = !autoTTS">
                <span class="switch" :class="{ on: autoTTS }" />
                <span class="text-xs">朗读</span>
                <Icon v-if="ttsBusy" name="volume" :size="14" class="text-primary" />
              </button>
            </div>
            <div class="row gap-2">
              <span class="text-xs text-dim hide-sm">{{ input.length ? `${input.length} 字` : '' }}</span>
              <button type="button" class="send" :disabled="!canSend" aria-label="发送" @click="handleSend()">
                <span v-if="chat.streaming" class="spinner spinner-xs" />
                <Icon v-else name="send" :size="16" />
              </button>
            </div>
          </div>
        </div>
      </footer>
    </section>

    <!-- 实时画像 -->
    <transition name="fade">
      <div v-if="panelOpen" class="panel-mask" @click="panelOpen = false" />
    </transition>
    <aside v-if="panelOpen" class="panel" aria-label="实时能力画像">
      <div class="panel-head">
        <span class="section-title"><Icon name="target" :size="16" /> 实时能力画像</span>
        <button type="button" class="btn btn-sm btn-ghost btn-icon" aria-label="关闭面板" @click="panelOpen = false">
          <Icon name="x" :size="15" />
        </button>
      </div>

      <div v-if="!chat.profile" class="empty panel-empty">
        <div class="empty-icon"><Icon name="chart" :size="22" /></div>
        <div class="empty-title">画像生成中</div>
        <div class="empty-desc">完成 1–2 轮作答后，这里会实时展示各维度表现与面试官的追问策略</div>
      </div>

      <div v-else class="panel-body">
        <div class="kpis">
          <div class="kpi">
            <span class="stat-label">已分析作答</span>
            <span class="kpi-value">{{ chat.profile.answer_count ?? chat.answerCount }}</span>
          </div>
          <div class="kpi">
            <span class="stat-label">画像置信度</span>
            <span class="kpi-value">{{ profileConfidence ?? '—' }}<small v-if="profileConfidence !== null">%</small></span>
          </div>
        </div>

        <div v-if="profileDimensions.length" class="dims">
          <div v-for="d in profileDimensions" :key="d.name" class="dim">
            <div class="dim-head">
              <span class="dim-name">{{ d.name }}</span>
              <span class="tag" :class="`tag-${scoreTone(d.score).cls}`">{{ scoreTone(d.score).text }}</span>
              <span class="dim-score">{{ d.score }}</span>
            </div>
            <div class="progress"><span :style="{ width: `${Math.min(100, d.score)}%`, background: `var(--${scoreTone(d.score).cls})` }" /></div>
            <p v-if="d.evidence" class="dim-evidence clamp-2" :title="d.evidence">{{ d.evidence }}</p>
          </div>
        </div>

        <div v-if="chat.profile.strengths?.length" class="block">
          <div class="block-title text-success"><Icon name="checkCircle" :size="14" /> 亮点</div>
          <ul><li v-for="s in chat.profile.strengths" :key="s">{{ s }}</li></ul>
        </div>
        <div v-if="chat.profile.gaps?.length" class="block">
          <div class="block-title text-warning"><Icon name="alert" :size="14" /> 待加强</div>
          <ul><li v-for="g in chat.profile.gaps" :key="g">{{ g }}</li></ul>
        </div>
        <div v-if="chat.profile.follow_up_strategy" class="block strategy">
          <div class="block-title text-primary"><Icon name="route" :size="14" /> 面试官追问策略</div>
          <p>{{ chat.profile.follow_up_strategy }}</p>
        </div>
      </div>

      <div class="panel-foot">
        <div class="tip">
          <Icon name="bulb" :size="14" />
          <span>卡壳时打开「教练」获取思路，教练对话不计入评估。</span>
        </div>
      </div>
    </aside>
  </div>
</template>

<style scoped>
/* ---------- 配置向导 ---------- */
.setup { padding: 32px 32px 48px; height: 100%; overflow-y: auto; }
@media (max-width: 768px) { .setup { padding: 18px 16px 28px; } }
.setup-head { margin-bottom: 20px; }
.setup-card { padding: 24px; }
.setup-foot {
  position: sticky; bottom: 0; z-index: 5;
  display: flex; align-items: center; gap: 16px; flex-wrap: wrap;
  margin-top: 16px; padding: 14px 18px;
  border-radius: var(--radius-lg); border: 1px solid var(--border);
  background: var(--bg-glass); backdrop-filter: blur(14px);
  box-shadow: var(--shadow-card);
}
.summary { flex: 1; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-width: 0; }

/* ---------- 面试室布局 ---------- */
.room { height: 100%; min-height: 0; display: flex; position: relative; }
.main { flex: 1; min-width: 0; display: flex; flex-direction: column; min-height: 0; }

.topbar {
  display: flex; align-items: center; gap: 16px;
  padding: 14px 24px; border-bottom: 1px solid var(--border);
  background: var(--bg-glass); backdrop-filter: blur(12px);
}
.topbar-info { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6px; }
.title-row { display: flex; align-items: center; gap: 8px; min-width: 0; }
.room-title { margin: 0; font-size: 16px; font-weight: 650; }
.status-row { display: flex; gap: 14px; flex-wrap: wrap; }
.status { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-dim); }
.topbar-actions { display: flex; align-items: center; gap: 6px; flex: none; }
.btn-icon.active { color: var(--primary); background: var(--primary-bg); }

.messages { flex: 1; overflow-y: auto; min-height: 0; scroll-behavior: smooth; }
.messages-inner { max-width: 860px; margin: 0 auto; padding: 24px 24px 12px; display: flex; flex-direction: column; gap: 18px; }
.restored-tip {
  align-self: center; display: inline-flex; align-items: center; gap: 6px;
  font-size: 12px; color: var(--text-dim); padding: 4px 12px;
  border-radius: var(--radius-pill); background: var(--bg-soft); border: 1px solid var(--border);
}

/* ---------- 输入区 ---------- */
.composer-wrap { padding: 8px 24px 20px; }
.composer-wrap > * { max-width: 860px; margin-left: auto; margin-right: auto; }
.quick { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.chip-sm { padding: 4px 10px; font-size: 12px; }
.chip:disabled { opacity: 0.5; cursor: not-allowed; }

.composer {
  border-radius: var(--radius-lg); border: 1px solid var(--border-strong);
  background: var(--bg-input); box-shadow: var(--shadow-soft);
  transition: border-color var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}
.composer:focus-within { border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-glow); }
.composer.coach { border-color: color-mix(in srgb, var(--coach) 50%, var(--border)); }
.composer.coach:focus-within { border-color: var(--coach); box-shadow: 0 0 0 3px color-mix(in srgb, var(--coach) 20%, transparent); }
.composer-input {
  display: block; width: 100%; resize: none; border: 0; outline: none; background: transparent;
  color: var(--text); font: inherit; font-size: 14.5px; line-height: 1.6;
  padding: 14px 16px 6px; max-height: 180px;
}
.composer-input::placeholder { color: var(--text-dim); }
.composer-bar { display: flex; align-items: center; justify-content: space-between; padding: 6px 10px 10px 10px; }
.tool {
  width: 34px; height: 34px; border-radius: var(--radius-sm); display: grid; place-items: center;
  color: var(--text-soft); transition: background var(--dur), color var(--dur);
}
.tool:hover { background: var(--bg-hover); color: var(--text); }
.tool.on { background: var(--danger-bg); color: var(--danger); }
.tool:focus-visible, .tool-switch:focus-visible, .send:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.sep { width: 1px; height: 18px; background: var(--border); margin: 0 6px; }
.tool-switch { display: inline-flex; align-items: center; gap: 6px; color: var(--text-soft); padding: 4px 6px; border-radius: var(--radius-sm); }
.tool-switch:hover { background: var(--bg-hover); }
.send {
  width: 36px; height: 36px; border-radius: 50%; display: grid; place-items: center;
  background: var(--gradient-primary); color: var(--text-on-primary);
  box-shadow: var(--shadow-glow); transition: transform var(--dur) var(--ease), opacity var(--dur);
}
.send:hover:not(:disabled) { transform: translateY(-1px); }
.send:disabled { opacity: 0.4; box-shadow: none; cursor: not-allowed; }
.spinner-xs { width: 14px; height: 14px; border-width: 2px; }

.asr-panel {
  margin-bottom: 10px; border-radius: var(--radius); border: 1px solid var(--border);
  background: var(--bg-soft); overflow: hidden;
}
.asr-head { display: flex; align-items: center; padding: 6px 8px 6px 12px; border-bottom: 1px solid var(--border); color: var(--text-soft); }
.asr-text { padding: 10px 12px; font-size: 13.5px; line-height: 1.6; max-height: 96px; overflow-y: auto; white-space: pre-wrap; }
.asr-text.placeholder { color: var(--text-dim); }

/* ---------- 实时画像 ---------- */
.panel {
  width: 320px; flex: none; display: flex; flex-direction: column; min-height: 0;
  border-left: 1px solid var(--border); background: var(--bg-soft);
}
.panel-mask { display: none; }
.panel-head { display: flex; align-items: center; justify-content: space-between; padding: 16px 16px 12px; }
.panel-body { flex: 1; overflow-y: auto; padding: 0 16px 16px; display: flex; flex-direction: column; gap: 16px; }
.panel-empty { flex: 1; padding: 32px 20px; }
.kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.kpi { padding: 12px; border-radius: var(--radius); background: var(--bg-card); border: 1px solid var(--border); display: flex; flex-direction: column; gap: 4px; }
.kpi-value { font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums; }
.kpi-value small { font-size: 13px; font-weight: 600; color: var(--text-dim); margin-left: 2px; }
.dims { display: flex; flex-direction: column; gap: 12px; padding: 14px; border-radius: var(--radius); background: var(--bg-card); border: 1px solid var(--border); }
.dim { display: flex; flex-direction: column; gap: 6px; }
.dim-head { display: flex; align-items: center; gap: 6px; }
.dim-name { font-size: 13px; font-weight: 600; flex: 1; min-width: 0; }
.dim-head .tag { padding: 0 6px; font-size: 11px; }
.dim-score { font-size: 13px; font-weight: 700; font-variant-numeric: tabular-nums; width: 26px; text-align: right; }
.dim-evidence { margin: 0; font-size: 12px; line-height: 1.5; color: var(--text-dim); }
.block { padding: 12px 14px; border-radius: var(--radius); background: var(--bg-card); border: 1px solid var(--border); }
.block-title { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; margin-bottom: 6px; }
.block ul { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 4px; }
.block li, .block p { font-size: 12.5px; line-height: 1.6; color: var(--text-soft); margin: 0; }
.strategy { background: var(--primary-bg); border-color: var(--primary-border); }
.panel-foot { padding: 12px 16px 16px; border-top: 1px solid var(--border); }
.tip { display: flex; gap: 8px; font-size: 12px; color: var(--text-dim); line-height: 1.5; }
.tip :deep(svg) { flex: none; margin-top: 2px; color: var(--warning); }

@media (max-width: 1100px) {
  .panel {
    position: fixed; top: 0; right: 0; bottom: 0; z-index: 301;
    width: min(360px, 92vw); box-shadow: var(--shadow); background: var(--bg-elevated);
    animation: slideIn 0.24s var(--ease);
  }
  .panel-mask { display: block; position: fixed; inset: 0; z-index: 300; background: var(--overlay); }
}
@keyframes slideIn { from { transform: translateX(100%); } to { transform: none; } }

@media (max-width: 768px) {
  .setup { padding: 16px 14px 32px; }
  .setup-card { padding: 16px; }
  .topbar { padding: 10px 14px; gap: 10px; }
  .status-row { display: none; }
  .hide-sm { display: none; }
  .messages-inner { padding: 16px 14px 8px; }
  .composer-wrap { padding: 6px 12px 12px; }
  .setup-foot .btn { width: 100%; justify-content: center; }
}
</style>
