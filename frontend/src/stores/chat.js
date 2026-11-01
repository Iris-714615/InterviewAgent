import { defineStore } from 'pinia'
import { createSession, chatStream, evaluate, getSessionMessages, getServiceStatus } from '../api'

// ============ 对话持久化(localStorage) ============
// 后端 SessionStore 已持久化消息,前端记住 sessionId 与配置,刷新后从后端恢复完整对话。
const STORAGE_KEY = 'interview_agent_current_session'

function loadFromLocal() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

function clearLocal() {
  try { localStorage.removeItem(STORAGE_KEY) } catch { /* ignore */ }
}

function newMessageId() {
  return globalThis.crypto?.randomUUID?.() || `local-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function normalizeMessage(message) {
  const channel = message.channel || (message.coach ? 'coach' : 'interview')
  return {
    message_id: message.message_id || newMessageId(),
    role: message.role,
    content: message.content,
    channel,
    model: message.model || '',
    route_reason: message.route_reason || '',
    retrieval: message.retrieval || [],
    demo: Boolean(message.demo),
    fallback: Boolean(message.fallback)
  }
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    sessionId: null,
    direction: 'ai_app_engineer',
    directionName: '',
    positionDescription: '',
    role: 'technical',
    messages: [],
    streaming: false,
    currentModel: null,
    streamMeta: {},
    rag: null,
    profile: null,
    demoMode: false,
    runtimeMode: 'normal',
    serviceStatus: null,
    serviceStatusError: '',
    evaluation: null,
    evaluating: false,
    coachMode: false,
    restored: false
  }),
  getters: {
    interviewMessages: (s) => s.messages.filter((m) => m.channel === 'interview'),
    messageCount() {
      return this.interviewMessages.length
    },
    answerCount() {
      return this.interviewMessages.filter((m) => m.role === 'user').length
    },
    hasMessages() {
      return this.interviewMessages.length > 0
    }
  },
  actions: {
    persist(withMessages = false) {
      try {
        const prev = loadFromLocal()
        localStorage.setItem(STORAGE_KEY, JSON.stringify({
          sessionId: this.sessionId,
          direction: this.direction,
          directionName: this.directionName,
          positionDescription: this.positionDescription,
          role: this.role,
          coachMode: this.coachMode,
          messages: (withMessages ? this.messages : (prev?.messages ?? [])).slice(-40)
        }))
      } catch { /* localStorage 不可用时静默降级 */ }
    },
    configure({ direction, directionName, role, positionDescription }) {
      if (direction) this.direction = direction
      if (directionName !== undefined) this.directionName = directionName
      if (role) this.role = role
      if (positionDescription !== undefined) this.positionDescription = positionDescription
    },
    async loadServiceStatus() {
      try {
        this.serviceStatus = await getServiceStatus()
        this.runtimeMode = this.serviceStatus.demo_mode ? 'demo' : (this.serviceStatus.status === 'ok' ? 'normal' : 'degraded')
        this.serviceStatusError = ''
      } catch {
        this.serviceStatus = null
        this.serviceStatusError = '当前可以继续基础练习'
      }
      return this.serviceStatus
    },
    async startSession() {
      const data = await createSession(this.direction, this.role, this.positionDescription)
      this.sessionId = data.session_id
      if (data.direction) this.direction = data.direction
      if (data.direction_name) this.directionName = data.direction_name
      this.evaluation = null
      this.streamMeta = {}
      this.rag = null
      this.profile = null
      this.demoMode = false
      this.restored = false
      this.persist()
      return data
    },
    async send(message) {
      if (this.streaming) return
      if (!this.sessionId) {
        try { await this.startSession() } catch { this.runtimeMode = 'guided' }
      }
      const previous = this.messages.map((m) => ({ role: m.role, content: m.content, channel: m.channel }))
      const channel = this.coachMode ? 'coach' : 'interview'
      this.messages.push(normalizeMessage({ role: 'user', content: message, channel }))
      this.messages.push(normalizeMessage({ role: 'assistant', content: '', channel }))
      const idx = this.messages.length - 1

      this.streaming = true
      const payload = {
        message,
        session_id: this.sessionId,
        direction: this.direction,
        role: this.role,
        use_rag: true,
        coach_mode: this.coachMode,
        history: previous
      }

      await chatStream(payload, {
        onMeta: (meta) => {
          this.streamMeta = meta
          this.currentModel = meta.model
          this.rag = meta.rag || null
          this.runtimeMode = meta.mode || (this.serviceStatus?.demo_mode ? 'demo' : this.serviceStatus?.status || 'normal')
          this.messages[idx].model = meta.model || ''
          if (meta.user_message_id) this.messages[idx - 1].message_id = meta.user_message_id
          if (meta.message_id) this.messages[idx].message_id = meta.message_id
          this.messages[idx].route_reason = meta.route_reason || ''
          this.messages[idx].retrieval = meta.retrieval || []
        },
        onProfile: (profile) => {
          this.profile = profile
        },
        onChunk: (chunk, data) => {
          this.messages[idx].content += chunk
          if (data.demo) this.messages[idx].demo = true
          if (data.fallback) this.messages[idx].fallback = true
        },
        onDone: (data) => {
          this.demoMode = Boolean(data?.demo)
          if (data?.fallback) {
            this.runtimeMode = 'guided'
            this.messages[idx].fallback = true
          }
          this.streaming = false
          this.persist(true)
        },
        onError: () => {
          const content = this.messages[idx].content
          this.messages[idx].content = content
            ? `${content}\n\n本轮回复中断。你可以继续补充回答或发送“继续”。`
            : this.coachMode
              ? '已切换到基础辅导。你可以按背景、任务、行动、结果整理回答，再说明自己的贡献。'
              : '已切换到基础练习。请介绍一个项目的目标、你的职责、技术方案和结果。'
          this.messages[idx].fallback = true
          this.messages[idx].model = ''
          this.messages[idx].route_reason = '基础练习引导'
          this.runtimeMode = 'guided'
          this.streaming = false
          this.persist(true)
        }
      })
    },
    resetRuntime() {
      this.evaluation = null
      this.currentModel = null
      this.rag = null
      this.profile = null
      this.demoMode = false
      this.streaming = false
    },
    async loadHistory(sessionId, info = null) {
      const msgs = await getSessionMessages(sessionId)
      this.sessionId = sessionId
      this.messages = msgs.map(normalizeMessage)
      if (info) {
        this.direction = info.direction || this.direction
        this.directionName = info.direction_name || ''
        this.positionDescription = info.position_description || ''
        this.role = info.role || this.role
      }
      this.resetRuntime()
      this.coachMode = false
      this.restored = true
      this.persist(true)
    },
    // 刷新后自动恢复上次未结束的会话；返回是否恢复成功
    async restoreFromLocal() {
      const saved = loadFromLocal()
      if (!saved?.sessionId) return false
      this.direction = saved.direction || this.direction
      this.directionName = saved.directionName || ''
      this.positionDescription = saved.positionDescription || ''
      this.role = saved.role || this.role
      this.coachMode = false
      try {
        const msgs = await getSessionMessages(saved.sessionId)
        if (!Array.isArray(msgs)) {
          clearLocal()
          return false
        }
        this.sessionId = saved.sessionId
        this.messages = msgs.map(normalizeMessage)
        this.resetRuntime()
        this.restored = this.messages.length > 0
        return this.restored
      } catch {
        this.sessionId = saved.sessionId
        this.messages = (saved.messages || []).map(normalizeMessage)
        this.runtimeMode = 'guided'
        this.restored = this.messages.length > 0
        return this.restored
      }
    },
    async runEvaluation() {
      if (!this.hasMessages) return
      this.evaluating = true
      try {
        const result = await evaluate({
          session_id: this.sessionId,
          direction: this.direction,
          role: this.role,
          messages: this.interviewMessages.map((m) => ({
            message_id: m.message_id,
            role: m.role,
            content: m.content,
            channel: 'interview'
          }))
        })
        this.evaluation = result
        return result
      } catch {
        this.evaluation = {
          status: 'failed', confidence: 0, overall_score: 0,
          dimensions: [], evidence: [], strengths: [], weaknesses: [],
          suggestions: [], warnings: [],
          summary: '这次反馈暂时无法生成。你的回答仍保留，可以稍后重试。'
        }
        return this.evaluation
      } finally {
        this.evaluating = false
      }
    },
    toggleCoachMode() {
      this.coachMode = !this.coachMode
      this.persist()
    },
    reset() {
      this.sessionId = null
      this.messages = []
      this.resetRuntime()
      this.restored = false
      clearLocal()
    }
  }
})
