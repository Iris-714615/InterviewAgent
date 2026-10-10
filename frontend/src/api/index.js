// 后端 API 封装：前端与后端通过同域名的 Nginx /api/ 代理通信。
const BASE = '/api/v1'
const CHAT_BASE = BASE

async function request(url, options = {}) {
  const headers = options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }
  const res = await fetch(url, { headers, ...options })
  if (!res.ok) {
    let message = '服务暂时不可用，请稍后重试'
    try {
      const data = await res.json()
      if (data?.detail && typeof data.detail === 'string') message = data.detail
    } catch (e) {}
    throw new Error(`请求失败 ${res.status}: ${message}`)
  }
  return res.json()
}

// ============ 面试会话 ============
export function createSession(direction, role) {
  return request(`${BASE}/interview/sessions?direction=${direction}&role=${role}`, { method: 'POST' })
}

export function listSessions() {
  return request(`${BASE}/interview/sessions`)
}

export function getSessionMessages(sessionId) {
  return request(`${BASE}/interview/sessions/${sessionId}/messages`)
}

export function getServiceStatus() {
  return request(`${BASE}/status`)
}

// ============ 面试对话(流式) ============
/**
 * 流式面试对话,通过 fetch + ReadableStream 解析 SSE。
 * @param {Object} payload - ChatRequest 字段
 * @param {Object} handlers - 回调集合
 * @param {(chunk: string) => void} handlers.onChunk - 收到文本块
 * @param {(meta: Object) => void} handlers.onMeta - 收到模型与 RAG 信息
 * @param {(profile: Object) => void} handlers.onProfile - 收到实时能力画像
 * @param {(done: Object) => void} handlers.onDone - 完成
 * @param {(err: Error) => void} handlers.onError - 错误
 */
export async function chatStream(payload, { onChunk, onMeta, onProfile, onDone, onError } = {}) {
  try {
    const res = await fetch(`${CHAT_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    if (!res.ok) throw new Error(`对话失败 ${res.status}`)

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finished = false

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      // SSE 事件以空行分隔,兼容 \r\n 和 \n 两种行尾
      const blocks = buffer.split(/\r?\n\r?\n/)
      buffer = blocks.pop() // 最后不完整的块留到下次

      for (const block of blocks) {
        const lines = block.split(/\r?\n/)
        let event = 'message'
        let data = ''
        for (const line of lines) {
          if (line.startsWith('event:')) event = line.slice(6).trim()
          else if (line.startsWith('data:')) data += line.slice(5).trim()
        }
        if (!data) continue
        try {
          const parsed = JSON.parse(data)
          if (event === 'error') {
            onError && onError(new Error(parsed.content || '未知错误'))
            return
          }
          if (event === 'done') {
            finished = true
            if (onDone) await onDone(parsed)
            return
          }
          if (event === 'meta') {
            onMeta && onMeta(parsed)
            continue
          }
          if (event === 'profile') {
            onProfile && onProfile(parsed)
            continue
          }
          if (parsed.content) onChunk && onChunk(parsed.content, parsed)
        } catch (e) {
          // 非 JSON,跳过
        }
      }
    }
    if (!finished) onDone && onDone({ finish: true })
  } catch (err) {
    onError && onError(err)
  }
}

// ============ 语音合成(TTS) ============
/**
 * 文本转语音,返回可直接播放的 blob URL。
 * @param {string} text
 * @returns {Promise<string>} objectURL
 */
export async function synthesizeTTS(text) {
  const res = await fetch(`${BASE}/tts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  })
  if (!res.ok) {
    const t = await res.text().catch(() => '')
    throw new Error(`语音合成失败 ${res.status}: ${t}`)
  }
  const blob = await res.blob()
  return URL.createObjectURL(blob)
}

// ============ 语音识别(ASR) ============
/**
 * 音频转文字,用于识别系统声音(如腾讯会议面试官)。
 * @param {Blob} audioBlob - 浏览器切片的音频(webm/wav)
 * @returns {Promise<string>} 识别出的文字
 */
export async function recognizeASR(audioBlob) {
  const formData = new FormData()
  // 文件名带 .webm 扩展名,后端据此选择解码器
  const ext = audioBlob.type.includes('webm') ? 'webm' : (audioBlob.type.includes('ogg') ? 'ogg' : 'wav')
  formData.append('file', audioBlob, `audio.${ext}`)
  const res = await fetch(`${BASE}/asr`, {
    method: 'POST',
    body: formData
  })
  if (!res.ok) {
    const t = await res.text().catch(() => '')
    throw new Error(`语音识别失败 ${res.status}: ${t}`)
  }
  const data = await res.json()
  return data.text || ''
}

// ============ 模型徽章(省钱可视化) ============
/** 模型全名 → 简短徽章标签 */
export function modelBadge(model) {
  if (!model) return ''
  if (model.includes('flash')) return 'flash'
  if (model.includes('pro')) return 'pro'
  if (model.includes('glm')) return 'glm'
  return model
}

// ============ 评估 ============
export function evaluate(payload) {
  return request(`${BASE}/evaluation`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })
}

export function getEvaluation(sessionId) {
  return request(`${BASE}/evaluation/${sessionId}`)
}

// ============ 资料库 ============
export function uploadFile(file, { documentType = 'other', sessionId = null, retentionDays = 30, redact = true } = {}) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('document_type', documentType)
  formData.append('retention_days', String(retentionDays))
  formData.append('redact', String(redact))
  if (sessionId) formData.append('session_id', sessionId)
  return request(`${BASE}/knowledge/upload`, { method: 'POST', body: formData })
}

export function listFiles(sessionId = null) {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
  return request(`${BASE}/knowledge/files${query}`).then((d) => d.files || [])
}

export function deleteDocument(documentId) {
  return request(`${BASE}/knowledge/documents/${encodeURIComponent(documentId)}`, { method: 'DELETE' })
}

export function generateProfile(sessionId, documentType = null) {
  const query = new URLSearchParams()
  query.set('session_id', sessionId)
  if (documentType) query.set('document_type', documentType)
  return request(`${BASE}/knowledge/profile/generate?${query}` , { method: 'POST' })
}

export function getProfiles(sessionId) {
  return request(`${BASE}/knowledge/profiles?session_id=${encodeURIComponent(sessionId)}`)
}

export function getPrivacyStatus(sessionId) {
  return request(`${BASE}/knowledge/privacy?session_id=${encodeURIComponent(sessionId)}`)
}

export function updatePrivacy(sessionId, retentionDays) {
  return request(`${BASE}/knowledge/privacy?session_id=${encodeURIComponent(sessionId)}`, { method: 'PUT', body: JSON.stringify({ retention_days: retentionDays }) })
}

export function clearPrivacyData() {
  return request(`${BASE}/privacy/data`, { method: 'DELETE' })
}

export function getGrowthSummary(sessionId) {
  return request(`${BASE}/evaluation/${encodeURIComponent(sessionId)}/growth`)
}

export function getRoutingMetrics(sessionId = null) {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
  return request(`${BASE}/metrics/routing${query}`)
}


export function retrieveKnowledge(query, topK = 4, sessionId = null, documentType = null) {
  const params = new URLSearchParams({ session_id: sessionId || '' })
  if (documentType) params.set('document_type', documentType)
  return request(`${BASE}/knowledge/retrieve?${params}`, {
    method: 'POST',
    body: JSON.stringify({ query, top_k: topK, session_id: sessionId, document_type: documentType })
  })
}
