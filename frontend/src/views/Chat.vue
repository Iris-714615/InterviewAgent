<script setup>
import { ref, watch, nextTick, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '../stores/chat'
import { recognizeASR } from '../api'
import { speakText, stopSpeech } from '../utils/speech'
import ChatMessage from '../components/ChatMessage.vue'

const router = useRouter()
const chat = useChatStore()

const input = ref('')
const scrollEl = ref(null)

// ============ 刷新后自动恢复上次对话 ============
const restoreTip = ref('') // 恢复提示文案
onMounted(async () => {
  // 已有会话(如从总览回顾)无需恢复
  chat.loadServiceStatus()
  if (chat.sessionId) return
  const ok = await chat.restoreFromLocal()
  if (ok) {
    restoreTip.value = `已恢复上次对话(${chat.messages.length} 条消息)`
    await scrollToBottom()
    // 4 秒后自动隐藏提示
    setTimeout(() => { restoreTip.value = '' }, 4000)
  }
})

const directions = [
  { value: 'ai_app_engineer', label: 'AI大模型应用' },
  { value: 'ai_dev_engineer', label: 'AI应用开发' },
  { value: 'ai_product_manager', label: 'AI产品经理' }
]
const roles = [
  { value: 'technical', label: '技术面' },
  { value: 'hr', label: 'HR面' },
  { value: 'behavioral', label: '行为面' }
]

const canSend = computed(() => input.value.trim() && !chat.streaming)
const profileDimensions = computed(() => Object.entries(chat.profile?.dimensions || {}).map(([name, value]) => ({
  name,
  score: Number(value?.score || 0),
  evidence: value?.evidence || ''
})))
const ragLabel = computed(() => ({
  used: '已启用', empty: '无匹配', disabled: '已关闭', unconfigured: '未配置', error: '资料暂不可用', fallback: '资料暂不可用', keyword: '本地检索', pending: '检索中'
}[chat.rag?.status] || '等待检索'))
const modeLabel = computed(() => ({ normal: '正常', ok: '正常', degraded: '基础练习', guided: '基础练习', demo: '演示' }[chat.runtimeMode] || chat.runtimeMode))
const profileConfidence = computed(() => {
  const value = chat.profile?.confidence
  return typeof value === 'number' ? `${Math.round(value * 100)}%` : '暂无数值'
})

function profileTrend(score) {
  if (score >= 80) return '强项'
  if (score >= 60) return '稳定'
  return '待提升'
}

async function scrollToBottom() {
  await nextTick()
  if (scrollEl.value) {
    scrollEl.value.scrollTop = scrollEl.value.scrollHeight
  }
}

async function handleSend() {
  stopAutoTTS()
  const msg = input.value.trim()
  if (!msg || chat.streaming) return
  input.value = ''
  await chat.send(msg)
  scrollToBottom()
}

function onKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function newInterview() {
  chat.reset()
}

async function finishAndEvaluate() {
  if (!chat.hasMessages) return
  await chat.runEvaluation()
  router.push('/report')
}

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
// 消息角色映射
const messageRoleMap = {
  user: '我',
  assistant: '面试官'
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

// 导出当前对话为 Markdown 文件
function exportChat() {
  if (!chat.hasMessages) return
  const now = new Date()
  const directionText = directionMap[chat.direction] || chat.direction
  const roleText = roleMap[chat.role] || chat.role
  const lines = []
  lines.push('# 模拟面试记录')
  lines.push('')
  lines.push(`- 方向:${directionText}`)
  lines.push(`- 角色:${roleText}`)
  lines.push(`- 时间:${formatTime(now)}`)
  lines.push(`- 消息数:${chat.messages.length}`)
  lines.push('')
  lines.push('---')
  lines.push('')
  for (const m of chat.messages) {
    // 带教练标记的消息显示为"教练提示"
    const speaker = m.channel === 'coach' ? (m.role === 'user' ? '向教练提问' : '教练提示') : messageRoleMap[m.role] || m.role
    lines.push(`### ${speaker}`)
    lines.push(m.content || '')
    lines.push('')
  }
  const md = lines.join('\n')
  const blob = new Blob([md], { type: 'text/markdown' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `面试记录_${makeTimestamp()}.md`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// ============ 语音输入(Web Speech API,大陆需翻墙) ============
// 持续监听模式:用户可以一直说,说完后再点击按钮停止
const recognizing = ref(false)
const speechSupported = ref(false)
const speechError = ref('') // 语音识别错误提示
let recognition = null

if (typeof window !== 'undefined') {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition
  if (SR) {
    speechSupported.value = true
    recognition = new SR()
    recognition.lang = 'zh-CN'
    recognition.continuous = true // 持续监听模式,需手动停止
    recognition.interimResults = true
    recognition.onresult = (e) => {
      let text = ''
      // 持续模式下可能有多段结果,拼接起来
      for (let i = 0; i < e.results.length; i++) {
        text += e.results[i][0].transcript
      }
      input.value = text
    }
    recognition.onend = () => { recognizing.value = false }
    recognition.onerror = (e) => {
      recognizing.value = false
      if (e.error === 'no-speech' || e.error === 'aborted') return
      // network: 大陆无法访问 Google 语音服务
      if (e.error === 'network') {
        speechError.value = '语音识别服务不可用(需联网访问 Google 服务),请使用文字输入,或开启 VPN 后重试'
      } else if (e.error === 'not-allowed') {
        speechError.value = '麦克风权限被拒绝,请在浏览器设置中允许'
      } else if (e.error === 'service-not-allowed') {
        speechError.value = '语音识别服务不可用,请使用 Chrome/Edge 浏览器'
      } else {
        speechError.value = '语音输入暂不可用，仍可打字回答。'
      }
      // 5 秒后自动清除提示
      setTimeout(() => { speechError.value = '' }, 5000)
    }
  }
}

function toggleVoice() {
  if (!recognition) return
  speechError.value = ''
  if (recognizing.value) {
    recognition.stop()
    recognizing.value = false
  } else {
    input.value = ''
    try {
      recognition.start()
      recognizing.value = true
    } catch (e) {
      recognizing.value = false
      speechError.value = '无法启动语音识别,请检查浏览器兼容性'
      setTimeout(() => { speechError.value = '' }, 5000)
    }
  }
}

// ============ 系统音频捕获(听面试官说话,如腾讯会议) ============
// 用 AudioWorklet 在音频线程采集 PCM,主线程定时切片并行上传 ASR
// 实现真正的边录边识别边显示,字幕持续追加
const listening = ref(false)        // 是否正在监听系统音频
const asrText = ref('')             // 累计识别的文字
const asrError = ref('')            // ASR 错误提示
const asrBusy = ref(false)          // 正在识别中(并行时可能多段)
let pendingCount = 0                // 当前并行识别中的段数
let displayStream = null             // getDisplayMedia 的流
let audioContext = null              // AudioContext 实例
let mediaSource = null               // MediaStreamSource 节点
let workletNode = null               // AudioWorkletNode 节点
let captureTimer = null             // 切片定时器
const CAPTURE_INTERVAL = 3000       // 切片时长(ms),3秒一段
const SAMPLE_RATE = 16000           // whisper 推荐采样率
const CHANNELS = 1                 // 单声道

async function toggleListen() {
  if (listening.value) {
    stopListening()
  } else {
    await startListening()
  }
}

async function startListening() {
  asrError.value = ''
  asrText.value = ''
  if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
    asrError.value = '当前浏览器不支持系统音频捕获,请使用 Chrome/Edge'
    setTimeout(() => { asrError.value = '' }, 5000)
    return
  }
  if (typeof AudioContext === 'undefined' && typeof webkitAudioContext === 'undefined') {
    asrError.value = '当前浏览器不支持 AudioContext,请升级浏览器'
    setTimeout(() => { asrError.value = '' }, 5000)
    return
  }

  try {
    // 必须请求 video:true,浏览器才会弹共享选择框
    displayStream = await navigator.mediaDevices.getDisplayMedia({
      video: true,
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
      },
    })
  } catch (e) {
    if (e.name === 'NotAllowedError') {
      asrError.value = '已取消屏幕共享,请重新点击并选择"共享系统音频"'
    } else if (e.name === 'NotReadableError') {
      asrError.value = '屏幕捕获被占用:请先停止腾讯会议/OBS 等的屏幕共享,再点 🔈 重试'
    } else {
      asrError.value = `无法获取屏幕共享(${e.name}):${e.message}`
    }
    setTimeout(() => { asrError.value = '' }, 8000)
    return
  }

  const audioTracks = displayStream.getAudioTracks()
  if (audioTracks.length === 0) {
    asrError.value = '未检测到系统音频,请在共享弹窗里勾选"共享系统音频"复选框'
    setTimeout(() => { asrError.value = '' }, 6000)
    stopDisplayStream()
    return
  }

  // 用户通过浏览器 UI 停止共享时,自动关闭监听
  audioTracks[0].addEventListener('ended', () => stopListening())

  // 立即停掉视频轨道,只保留音频(省资源)
  displayStream.getVideoTracks().forEach((t) => t.stop())

  // 创建 AudioContext,采样率设为 16kHz(whisper 最佳采样率)
  const AudioCtx = AudioContext || webkitAudioContext
  audioContext = new AudioCtx({ sampleRate: SAMPLE_RATE })

  // 加载 AudioWorklet 模块
  try {
    await audioContext.audioWorklet.addModule(new URL('../worklets/recorder-processor.js', import.meta.url))
  } catch (e) {
    asrError.value = '录音暂不可用，仍可打字回答。'
    setTimeout(() => { asrError.value = '' }, 5000)
    stopDisplayStream()
    return
  }

  // 连接音频流
  const audioStream = new MediaStream(audioTracks)
  mediaSource = audioContext.createMediaStreamSource(audioStream)
  workletNode = new AudioWorkletNode(audioContext, 'recorder-processor', {
    numberOfInputs: 1,
    numberOfOutputs: 1,
    channelCount: CHANNELS,
  })

  // source → worklet(不连到 destination,避免系统声音被回放出来)
  mediaSource.connect(workletNode)

  // 监听 worklet 返回的数据
  workletNode.port.onmessage = async (e) => {
    const { samples, length } = e.data
    if (!samples || length === 0) return
    // 异步处理这一段,不阻塞 worklet
    processChunk(samples)
  }

  listening.value = true
  pendingCount = 0

  // 启动切片定时器:定时向 worklet 要数据
  captureTimer = setInterval(() => flushFromWorklet(), CAPTURE_INTERVAL)
}

// 从 worklet 取出当前累积的 PCM 数据
function flushFromWorklet() {
  if (!listening.value || !workletNode) return
  // 向 worklet 发指令,让它把累积的数据返回
  workletNode.port.postMessage('flush')
}

// 处理一段 PCM 数据:编码 WAV + 并行上传 ASR + 追加显示
async function processChunk(samples) {
  // 检测音量(避免识别静音段浪费时间)
  let maxSample = 0
  for (let i = 0; i < samples.length; i++) {
    const abs = Math.abs(samples[i])
    if (abs > maxSample) maxSample = abs
  }
  if (maxSample < 0.01) return // 静音段跳过

  // 编码 WAV
  const wavBlob = encodeWav(samples, SAMPLE_RATE, CHANNELS)

  // 并行上传:不阻塞后续切片
  pendingCount++
  asrBusy.value = true
  try {
    const text = await recognizeASR(wavBlob)
    if (text) {
      // 关键:识别到就立即追加显示,不等下一段
      asrText.value = asrText.value
        ? asrText.value + text
        : text
    }
  } catch (e) {
    asrError.value = e.message
    setTimeout(() => { asrError.value = '' }, 5000)
  } finally {
    pendingCount--
    asrBusy.value = pendingCount > 0
  }
}

// 把 Float32Array PCM 编码成 WAV Blob(16-bit PCM)
function encodeWav(samples, sampleRate, channels) {
  const bytesPerSample = 2
  const blockAlign = channels * bytesPerSample
  const dataSize = samples.length * bytesPerSample
  const buffer = new ArrayBuffer(44 + dataSize)
  const view = new DataView(buffer)

  writeString(view, 0, 'RIFF')
  view.setUint32(4, 36 + dataSize, true)
  writeString(view, 8, 'WAVE')
  writeString(view, 12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, channels, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * blockAlign, true)
  view.setUint16(32, blockAlign, true)
  view.setUint16(34, bytesPerSample * 8, true)
  writeString(view, 36, 'data')
  view.setUint32(40, dataSize, true)

  let offset = 44
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    offset += 2
  }

  return new Blob([buffer], { type: 'audio/wav' })
}

function writeString(view, offset, str) {
  for (let i = 0; i < str.length; i++) {
    view.setUint8(offset + i, str.charCodeAt(i))
  }
}

function stopListening() {
  listening.value = false
  if (captureTimer) {
    clearInterval(captureTimer)
    captureTimer = null
  }
  if (workletNode) {
    try { workletNode.port.postMessage('flush') } catch (e) {}
    try { workletNode.disconnect() } catch (e) {}
    workletNode = null
  }
  if (mediaSource) {
    try { mediaSource.disconnect() } catch (e) {}
    mediaSource = null
  }
  if (audioContext) {
    try { audioContext.close() } catch (e) {}
    audioContext = null
  }
  pendingCount = 0
  asrBusy.value = false
  stopDisplayStream()
}

function stopDisplayStream() {
  if (displayStream) {
    displayStream.getTracks().forEach((t) => t.stop())
    displayStream = null
  }
}

// 把识别结果填入输入框,方便用户直接发送
function useAsrAsInput() {
  if (!asrText.value) return
  input.value = asrText.value
  asrText.value = ''
}

// 清空识别文本
function clearAsrText() {
  asrText.value = ''
}

// 组件卸载时清理资源
onBeforeUnmount(() => {
  stopListening()
  stopAutoTTS()
})

// ============ 语音输出(自动朗读面试官回复) ============
const autoTTS = ref(false)
let autoSpeechController = null
let spokenLength = 0
let speakingMessageId = null
let speechQueue = Promise.resolve()
const ttsBusy = ref(false)

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
    try { await speakText(text, controller.signal) }
    catch (e) { /* Text remains available in the conversation. */ }
  }).finally(() => { if (controller === autoSpeechController) ttsBusy.value = false })
}

// Start reading a completed sentence while the answer is still streaming.
watch(() => chat.messages.at(-1)?.content || '', (content) => {
  const last = chat.messages.at(-1)
  if (!autoTTS.value || !last || last.role !== 'assistant' || last.channel !== 'interview') return
  if (speakingMessageId !== last.message_id) {
    stopAutoTTS()
    speakingMessageId = last.message_id
    autoSpeechController = new AbortController()
  }
  const remaining = content.slice(spokenLength)
  const complete = remaining.match(/^[\s\S]*?[。！？!?\n]/)
  if (complete) {
    spokenLength += complete[0].length
    queueSpeech(complete[0])
  }
})

watch(() => chat.streaming, (streaming, prev) => {
  if (prev && !streaming && autoTTS.value) {
    const last = chat.messages.at(-1)
    if (last?.role === 'assistant' && last.channel === 'interview') {
      if (!autoSpeechController) autoSpeechController = new AbortController()
      queueSpeech(last.content.slice(spokenLength))
      spokenLength = last.content.length
    }
  }
})
watch(autoTTS, (on) => { if (!on) stopAutoTTS() })
// 监听消息变化自动滚动
watch(
  () => chat.messages.length,
  () => scrollToBottom()
)
watch(
  () => chat.messages.map((m) => m.content).join(''),
  () => {
    if (chat.streaming) scrollToBottom()
  }
)
</script>

<template>
  <div class="chat-page">
    <!-- 顶部配置栏 -->
    <div class="config-bar card">
      <div class="config-row">
        <div class="config-group">
          <span class="config-label">方向</span>
          <select v-model="chat.direction" class="select" :disabled="chat.hasMessages">
            <option v-for="d in directions" :key="d.value" :value="d.value">{{ d.label }}</option>
          </select>
        </div>
        <div class="config-group">
          <span class="config-label">角色</span>
          <select v-model="chat.role" class="select" :disabled="chat.hasMessages">
            <option v-for="r in roles" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
        </div>
        <button
          class="btn btn-coach"
          :class="{ active: chat.coachMode }"
          @click="chat.toggleCoachMode"
          :title="'开启后,你的提问将交给教练给出参考答案与思路'"
        >
          🎓 {{ chat.coachMode ? '辅导中' : '实时辅导' }}
        </button>
        <div class="spacer"></div>
        <button class="btn btn-ghost" @click="newInterview" :disabled="chat.streaming">
          ↻ 新面试
        </button>
        <button
          v-if="chat.hasMessages"
          class="btn btn-ghost"
          @click="exportChat"
          :disabled="chat.streaming"
        >
          ⬇ 导出对话
        </button>
        <button
          class="btn btn-primary"
          @click="finishAndEvaluate"
          :disabled="!chat.hasMessages || chat.streaming || chat.evaluating"
        >
          {{ chat.evaluating ? '评估中…' : '结束并评估' }}
        </button>
      </div>
      <div v-if="chat.coachMode" class="coach-tip">
        <span class="tag tag-coach">辅导模式</span>
        接下来你输入的内容,教练会直接给出参考答案与思路(不会进入面试对话)
      </div>
      <div class="insight-strip">
        <span class="status-chip" :class="`mode-${chat.runtimeMode}`">服务：{{ modeLabel }}</span>
        <span class="status-chip" :class="`rag-${chat.rag?.status || 'pending'}`">
          RAG：{{ ragLabel }}<template v-if="chat.rag?.count">（{{ chat.rag.count }} 条）</template>
        </span>
        <span v-if="chat.rag?.sources?.length" class="source-text" :title="chat.rag.sources.join('、')">
          来源：{{ chat.rag.sources.join('、') }}
        </span>
        <span v-if="routeSummary" class="source-text" :title="`实际成本 ${chat.routingMetrics.estimated_cost}，平均延迟 ${chat.routingMetrics.average_latency_ms}ms`">
          路由：{{ routeSummary }}
        </span>
        <span v-if="chat.serviceStatusError" class="status-error">{{ chat.serviceStatusError }}</span>
      </div>
      <!-- 刷新后恢复提示 -->
      <div v-if="restoreTip" class="restore-tip">
        <span class="restore-icon">↺</span>
        <span>{{ restoreTip }}</span>
        <button class="restore-close" @click="restoreTip = ''">×</button>
      </div>
    </div>

    <div v-if="chat.profile" class="profile-card card">
      <div class="profile-head">
        <div>
          <strong>实时能力画像</strong>
          <span class="profile-count">已分析 {{ chat.profile.answer_count || 0 }} 个回答</span>
        </div>
        <span class="confidence">置信度：{{ profileConfidence }}</span>
      </div>
      <div v-if="profileDimensions.length" class="profile-dimensions">
        <div v-for="d in profileDimensions" :key="d.name" class="profile-dimension" :title="d.evidence">
          <div class="profile-dim-head"><span>{{ d.name }}</span><b>{{ d.score.toFixed(0) }}</b></div>
          <div class="profile-bar"><span :style="{ width: `${d.score}%` }"></span></div>
          <small>{{ profileTrend(d.score) }}<template v-if="d.evidence"> · {{ d.evidence }}</template></small>
        </div>
      </div>
      <div class="profile-focus">
        <div v-if="chat.profile.strengths?.length"><b>重点：</b>{{ chat.profile.strengths.join('、') }}</div>
        <div v-if="chat.profile.gaps?.length" class="profile-gaps"><b>薄弱项：</b>{{ chat.profile.gaps.join('、') }}</div>
        <div v-if="chat.profile.follow_up_strategy"><b>追问策略：</b>{{ chat.profile.follow_up_strategy }}</div>
      </div>
    </div>

    <!-- 消息列表 -->
    <div ref="scrollEl" class="messages">
      <div v-if="!chat.hasMessages" class="empty">
        <div class="empty-icon">🎤</div>
        <div class="empty-title">准备好了就开始吧</div>
        <div class="empty-desc">
          选择面试方向与角色,发送「开始面试」即可。<br />
          面试中卡壳了,可点「实时辅导」求助教练。
        </div>
      </div>
      <template v-else>
        <ChatMessage
          v-for="(m, i) in chat.messages"
          :key="m.message_id"
          :role="m.role"
          :content="m.content"
          :coach="m.channel === 'coach'"
          :model="m.model"
          :route-reason="m.route_reason"
          :retrieval="m.retrieval"
          :streaming="chat.streaming && i === chat.messages.length - 1 && m.role === 'assistant'"
        />
      </template>
    </div>

    <!-- 输入区 -->
    <div class="input-bar">
      <!-- 面试官实时字幕(系统音频识别) -->
      <div v-if="listening || asrText" class="asr-panel">
        <div class="asr-header">
          <span class="asr-title">
            <span v-if="listening" class="asr-rec-dot" :class="{ busy: asrBusy }"></span>
            {{ listening ? (asrBusy ? '识别中…' : '正在听面试官说话') : '面试官说的话' }}
          </span>
          <div class="asr-actions">
            <button v-if="asrText" class="asr-btn" @click="useAsrAsInput" title="把识别文字填入输入框">填入</button>
            <button v-if="asrText" class="asr-btn" @click="clearAsrText" title="清空识别文字">清空</button>
          </div>
        </div>
        <div class="asr-text" :class="{ empty: !asrText }">{{ asrText || '等待识别结果…' }}</div>
      </div>
      <div class="input-wrap">
        <textarea
          v-model="input"
          class="textarea"
          :placeholder="chat.coachMode ? '向教练提问,获取参考答案…' : '输入你的回答 / 发送「开始面试」'"
          rows="1"
          @keydown="onKeydown"
          :disabled="chat.streaming"
        ></textarea>
        <button
          class="btn voice-btn listen-btn"
          :class="{ recording: listening }"
          @click="toggleListen"
          :disabled="chat.streaming"
          :title="listening ? '点击停止监听' : '听面试官说话(捕获系统音频)'"
        >
          <span v-if="listening" class="voice-dot"></span>
          <span v-else class="voice-icon">🔈</span>
        </button>
        <button
          v-if="speechSupported"
          class="btn voice-btn"
          :class="{ recording: recognizing }"
          @click="toggleVoice"
          :disabled="chat.streaming"
          :title="recognizing ? '点击停止识别' : '语音输入'"
        >
          <span v-if="recognizing" class="voice-dot"></span>
          <span v-else class="voice-icon">🎤</span>
        </button>
        <button class="btn btn-primary send-btn" @click="handleSend" :disabled="!canSend">
          {{ chat.streaming ? '…' : '发送' }}
        </button>
      </div>
      <div class="input-hint text-soft">
        <span v-if="asrError" class="voice-error">{{ asrError }}</span>
        <span v-if="speechError" class="voice-error">{{ speechError }}</span>
        <span v-if="chat.currentModel" class="cur-model">当前模型:{{ chat.currentModel }}</span>
        <label v-if="speechSupported" class="auto-tts-toggle">
          <input type="checkbox" v-model="autoTTS" />
          <span>自动朗读面试官回复</span>
        </label>
        <span v-else-if="!speechSupported" class="tts-warn">当前浏览器不支持语音输入,请使用 Chrome/Edge</span>
        <span>Enter 发送 · Shift+Enter 换行</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-width: 980px;
  margin: 0 auto;
  width: 100%;
}
.config-bar {
  margin-bottom: 16px;
  padding: 14px 18px;
}
.config-row {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.config-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
.config-label {
  font-size: 13px;
  color: var(--text-soft);
}
.select {
  padding: 8px 12px;
  font-size: 14px;
}
.spacer {
  flex: 1;
}
.coach-tip {
  margin-top: 10px;
  font-size: 13px;
  color: var(--text-soft);
  display: flex;
  align-items: center;
  gap: 8px;
}
.insight-strip {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
  font-size: 12px;
}
.status-chip {
  padding: 3px 9px;
  border: 1px solid var(--border);
  border-radius: var(--radius-pill);
  color: var(--text-soft);
}
.mode-normal, .mode-ok, .rag-used { color: var(--success); border-color: rgba(52, 211, 153, .35); }
.mode-degraded, .rag-empty, .rag-unconfigured { color: var(--warning); border-color: rgba(245, 158, 11, .35); }
.mode-demo { color: var(--danger); border-color: rgba(239, 68, 68, .35); }
.source-text { color: var(--text-soft); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 360px; }
.status-error { color: var(--danger); }
.profile-card { margin-bottom: 12px; padding: 14px 18px; }
.profile-head, .profile-dim-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.profile-count, .confidence { margin-left: 10px; color: var(--text-soft); font-size: 12px; }
.profile-dimensions { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin-top: 12px; }
.profile-dimension { min-width: 0; font-size: 13px; }
.profile-dimension small { display: block; margin-top: 4px; color: var(--text-soft); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.profile-bar { height: 5px; margin-top: 5px; border-radius: 3px; overflow: hidden; background: var(--bg-hover); }
.profile-bar span { display: block; height: 100%; background: var(--gradient-primary); }
.profile-focus { display: grid; gap: 5px; margin-top: 12px; font-size: 12px; color: var(--text-soft); }
.profile-gaps { color: var(--warning); }
.restore-tip {
  margin-top: 10px;
  padding: 8px 14px;
  background: rgba(52, 211, 153, 0.12);
  border: 1px solid rgba(52, 211, 153, 0.3);
  border-radius: var(--radius-sm);
  color: #6ee7b7;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
  animation: fadeInUp 0.3s ease;
}
.restore-icon {
  font-size: 16px;
  font-weight: 700;
}
.restore-tip span:nth-child(2) {
  flex: 1;
}
.restore-close {
  background: none;
  border: none;
  color: inherit;
  font-size: 18px;
  line-height: 1;
  padding: 0 4px;
  opacity: 0.6;
  cursor: pointer;
}
.restore-close:hover {
  opacity: 1;
}

.messages {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0 16px;
}
.empty {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: var(--text-soft);
  text-align: center;
}
.empty-icon {
  font-size: 56px;
  margin-bottom: 16px;
  opacity: 0.7;
}
.empty-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 8px;
}
.empty-desc {
  font-size: 14px;
  line-height: 1.8;
}

.input-bar {
  border-top: 1px solid var(--border);
  padding: 14px 0 4px;
}
.input-wrap {
  display: flex;
  gap: 10px;
  align-items: flex-end;
}
.textarea {
  flex: 1;
  min-height: 44px;
  max-height: 140px;
  padding: 12px 14px;
}
.voice-btn {
  height: 44px;
  width: 44px;
  flex-shrink: 0;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  background: var(--bg-hover);
  border: 1px solid var(--border);
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 18px;
}
.voice-btn:hover:not(:disabled) {
  border-color: rgba(99, 102, 241, 0.4);
  background: rgba(99, 102, 241, 0.1);
}
.voice-btn:disabled {
  opacity: 0.5;
  cursor: default;
}
.voice-btn.recording {
  background: rgba(239, 68, 68, 0.15);
  border-color: rgba(239, 68, 68, 0.5);
  animation: voicePulse 1.4s ease-in-out infinite;
}
.voice-icon {
  font-size: 18px;
  line-height: 1;
}
.voice-dot {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #ef4444;
  box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
  animation: dotPulse 1.4s ease-in-out infinite;
}
@keyframes voicePulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.5); }
  50% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
}
@keyframes dotPulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.3); opacity: 0.7; }
}
.send-btn {
  height: 44px;
  flex-shrink: 0;
}
.input-hint {
  font-size: 12px;
  margin-top: 6px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.cur-model {
  color: var(--primary);
  font-weight: 500;
}
.auto-tts-toggle {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  cursor: pointer;
  color: var(--text-soft);
  user-select: none;
}
.auto-tts-toggle input {
  margin: 0;
  cursor: pointer;
  accent-color: var(--primary);
}
.tts-warn {
  color: var(--warning, #f59e0b);
}
.voice-error {
  color: #fca5a5;
  background: rgba(239, 68, 68, 0.12);
  padding: 3px 10px;
  border-radius: var(--radius-pill);
  border: 1px solid rgba(239, 68, 68, 0.3);
  font-size: 12px;
}

/* ============ 系统音频识别字幕面板 ============ */
.asr-panel {
  margin-bottom: 10px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.25);
  border-radius: var(--radius-sm);
  overflow: hidden;
  animation: fadeInUp 0.25s ease;
}
.asr-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px 4px;
}
.asr-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-soft);
  font-weight: 500;
}
.asr-rec-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #ef4444;
  box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
  animation: dotPulse 1.4s ease-in-out infinite;
}
.asr-rec-dot.busy {
  background: #f59e0b;
  animation: dotPulse 0.8s ease-in-out infinite;
}
.asr-actions {
  display: flex;
  gap: 6px;
}
.asr-btn {
  background: rgba(99, 102, 241, 0.12);
  border: 1px solid rgba(99, 102, 241, 0.3);
  color: var(--primary, #818cf8);
  padding: 2px 10px;
  border-radius: var(--radius-pill);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.asr-btn:hover {
  background: rgba(99, 102, 241, 0.22);
  border-color: rgba(99, 102, 241, 0.5);
}
.asr-text {
  padding: 0 12px 10px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text);
  max-height: 120px;
  overflow-y: auto;
  word-break: break-word;
}
.asr-text.empty {
  color: var(--text-soft);
  font-style: italic;
  opacity: 0.7;
}
/* 听面试官说话按钮 - 用蓝色区分于麦克风语音输入 */
.listen-btn.recording {
  background: rgba(99, 102, 241, 0.15);
  border-color: rgba(99, 102, 241, 0.5);
  animation: voicePulse 1.4s ease-in-out infinite;
}
.listen-btn .voice-dot {
  background: #818cf8;
  box-shadow: 0 0 0 0 rgba(99, 102, 241, 0.7);
}

@media (max-width: 768px) {
  .config-bar {
    padding: 12px 14px;
    margin-bottom: 12px;
  }
  .config-row {
    gap: 8px;
  }
  .select {
    padding: 9px 10px;
    font-size: 13px;
    flex: 1;
    min-width: 0;
  }
  .config-group {
    flex: 1;
    min-width: 0;
  }
  .btn {
    padding: 9px 14px;
    font-size: 13px;
  }
  .config-label {
    display: none;
  }
  .profile-dimensions {
    grid-template-columns: 1fr;
  }
  .profile-head {
    align-items: flex-start;
  }
  .confidence {
    margin-left: 0;
    white-space: nowrap;
  }
  .source-text {
    max-width: 100%;
  }
  .spacer {
    display: none;
  }
  /* 输入区提示:仅保留自动朗读开关,其它提示隐藏以节省空间 */
  .input-hint {
    justify-content: flex-start;
  }
  .input-hint .cur-model,
  .input-hint > span:last-child {
    display: none;
  }
  .input-hint .auto-tts-toggle {
    font-size: 12px;
  }
  /* 触摸目标更大,避免误触 */
  .voice-btn,
  .send-btn {
    height: 46px;
  }
  .voice-btn {
    width: 46px;
  }
  .textarea {
    min-height: 46px;
  }
}

@media (max-width: 380px) {
  /* 极窄屏:进一步压缩按钮文字 */
  .btn {
    padding: 8px 10px;
    font-size: 12px;
  }
  .config-row {
    gap: 6px;
  }
}
</style>
