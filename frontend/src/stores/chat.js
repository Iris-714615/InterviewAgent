import { defineStore } from 'pinia'
import { createSession, chatStream, evaluate, getSessionMessages } from '../api'

// ============ 对话持久化(localStorage) ============
// 后端 SessionStore 已把消息写入 data/sessions.json,前端只需记住 sessionId,
// 刷新后通过 getSessionMessages 从后端恢复完整对话,彻底解决刷新丢失问题。
const STORAGE_KEY = 'interview_agent_current_session'

function saveToLocal({ sessionId, direction, role, coachMode }) {
  try {
    if (!sessionId) {
      localStorage.removeItem(STORAGE_KEY)
      return
    }
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ sessionId, direction, role, coachMode })
    )
  } catch (e) {
    // localStorage 不可用(隐私模式等),静默降级
  }
}

function loadFromLocal() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    return JSON.parse(raw)
  } catch (e) {
    return null
  }
}

function clearLocal() {
  try {
    localStorage.removeItem(STORAGE_KEY)
  } catch (e) {
    // ignore
  }
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    // 当前会话
    sessionId: null,
    direction: 'ai_app_engineer',
    role: 'technical',
    messages: [], // {role: 'user'|'assistant', content, coach?, model?}
    streaming: false,
    // 当前回复使用的模型(省钱可视化)
    currentModel: null,
    // 评估结果
    evaluation: null,
    evaluating: false,
    // 实时辅导模式
    coachMode: false,
    // 是否刚从历史恢复(用于 UI 提示)
    restored: false
  }),
  getters: {
    messageCount: (s) => s.messages.length,
    hasMessages: (s) => s.messages.length > 0
  },
  actions: {
    async startSession() {
      const data = await createSession(this.direction, this.role)
      this.sessionId = data.session_id
      this.messages = []
      this.evaluation = null
      this.restored = false
      saveToLocal({
        sessionId: this.sessionId,
        direction: this.direction,
        role: this.role,
        coachMode: this.coachMode
      })
      return data
    },
    async send(message) {
      if (this.streaming) return
      if (!this.sessionId) await this.startSession()

      // 加入用户消息
      this.messages.push({ role: 'user', content: message })
      // 占位 assistant 消息(通过索引访问 Pinia 响应式代理对象,确保修改触发重新渲染)
      this.messages.push({ role: 'assistant', content: '', coach: this.coachMode, model: '' })
      const idx = this.messages.length - 1

      this.streaming = true
      const payload = {
        message,
        session_id: this.sessionId,
        direction: this.direction,
        role: this.role,
        use_rag: true,
        coach_mode: this.coachMode
      }

      await chatStream(payload, {
        onMeta: (model) => {
          this.currentModel = model
          this.messages[idx].model = model
        },
        onChunk: (chunk) => {
          this.messages[idx].content += chunk
        },
        onDone: () => {
          this.streaming = false
          // 流式完成后持久化最新会话信息
          saveToLocal({
            sessionId: this.sessionId,
            direction: this.direction,
            role: this.role,
            coachMode: this.coachMode
          })
        },
        onError: (err) => {
          // 区分错误类型,给出更友好的提示
          const msg = err.message || ''
          if (msg.includes('Failed to fetch') || msg.includes('ERR_ABORTED')) {
            this.messages[idx].content = '⚠️ 连接失败:后端服务未启动或网络中断,请稍后重试'
          } else if (msg.includes('对话失败 5')) {
            this.messages[idx].content = `⚠️ 服务端错误:${msg}`
          } else {
            this.messages[idx].content = `⚠️ 出错了:${msg}`
          }
          this.streaming = false
        }
      })
    },
    async loadHistory(sessionId, info = null) {
      const msgs = await getSessionMessages(sessionId)
      this.sessionId = sessionId
      this.messages = msgs.map((m) => ({ role: m.role, content: m.content }))
      // 同步方向/角色,让回顾的对话上下文一致
      if (info) {
        this.direction = info.direction
        this.role = info.role
      }
      this.evaluation = null
      this.currentModel = null
      this.coachMode = false
      this.streaming = false
      this.restored = true
      saveToLocal({
        sessionId: this.sessionId,
        direction: this.direction,
        role: this.role,
        coachMode: this.coachMode
      })
    },
    // ============ 刷新后自动恢复 ============
    // 从 localStorage 读取上次未结束的会话,从后端拉取完整对话记录。
    // 返回 true 表示已恢复,false 表示无历史可恢复。
    async restoreFromLocal() {
      const saved = loadFromLocal()
      if (!saved || !saved.sessionId) return false
      try {
        const msgs = await getSessionMessages(saved.sessionId)
        // 后端会话已被删除/不存在 → 清理本地记录
        if (!Array.isArray(msgs)) {
          clearLocal()
          return false
        }
        this.sessionId = saved.sessionId
        this.direction = saved.direction || this.direction
        this.role = saved.role || this.role
        this.coachMode = false // 恢复时关闭辅导模式,避免误触
        this.messages = msgs.map((m) => ({ role: m.role, content: m.content }))
        this.evaluation = null
        this.currentModel = null
        this.streaming = false
        this.restored = true
        return this.messages.length > 0
      } catch (e) {
        // 会话不存在或后端未启动,清理本地记录
        clearLocal()
        return false
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
          messages: this.messages.map((m) => ({ role: m.role, content: m.content }))
        })
        this.evaluation = result
        return result
      } finally {
        this.evaluating = false
      }
    },
    toggleCoachMode() {
      this.coachMode = !this.coachMode
      saveToLocal({
        sessionId: this.sessionId,
        direction: this.direction,
        role: this.role,
        coachMode: this.coachMode
      })
    },
    reset() {
      this.sessionId = null
      this.messages = []
      this.evaluation = null
      this.streaming = false
      this.currentModel = null
      this.restored = false
      clearLocal()
    }
  }
})
