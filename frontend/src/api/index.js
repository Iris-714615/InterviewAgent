// 后端 API 封装：前端与后端通过同域名的 Nginx /api/ 代理通信。
const BASE = '/api/v1'
const CHAT_BASE = BASE

export const TOKEN_KEY = 'interview-agent-token'
export const getToken = () => {
  try { return localStorage.getItem(TOKEN_KEY) || '' } catch { return '' }
}
export const setToken = (t) => {
  try { t ? localStorage.setItem(TOKEN_KEY, t) : localStorage.removeItem(TOKEN_KEY) } catch { /* ignore */ }
}

// 登录失效时由 auth store 注册回调
let onUnauthorized = null
export function setUnauthorizedHandler(fn) { onUnauthorized = fn }

async function request(url, options = {}) {
  const { timeoutMs = 20000, headers: extraHeaders, ...fetchOptions } = options
  const headers = { ...(fetchOptions.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...extraHeaders }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let res
  try {
    res = await fetch(url, { ...fetchOptions, headers, signal: AbortSignal.timeout(timeoutMs) })
  } catch (e) {
    throw new Error('服务连接较慢，请稍后重试。已输入的内容仍在当前页面。')
  }
  if (!res.ok) {
    let detail = ''
    let requestId = ''
    try {
      const data = await res.json()
      detail = typeof data?.detail === 'string' ? data.detail : Array.isArray(data?.detail) ? '请检查填写的内容是否完整' : ''
      requestId = data?.request_id || ''
    } catch { /* ignore */ }
    if (res.status === 401 && token && onUnauthorized) onUnauthorized()
    const err = new Error(detail || fallbackMessage(res.status))
    err.status = res.status
    err.requestId = requestId
    throw err
  }
  if (res.status === 204) return null
  try {
    return await res.json()
  } catch {
    throw new Error('服务返回了无法识别的内容，请稍后重试。')
  }
}

function fallbackMessage(status) {
  if (status === 401) return '登录已失效，请重新登录。'
  if (status === 403) return '没有权限执行此操作。'
  if (status === 404) return '请求的内容不存在或已被删除。'
  if (status === 429) return '操作过于频繁，请稍后再试。'
  if (status >= 500) return '服务暂时不可用，请稍后重试。'
  return '暂时无法完成此操作，请稍后重试。'
}

// 读取错误响应中的 detail(流式/音频接口共用)
async function readErrorMessage(res) {
  try {
    const data = await res.json()
    if (typeof data?.detail === 'string' && data.detail) return data.detail
  } catch { /* ignore */ }
  return fallbackMessage(res.status)
}

// 直接使用 fetch 的接口(流式/音频)共用:附带 token,401 时触发登录失效处理
function authHeaders(base = {}) {
  const token = getToken()
  return token ? { ...base, Authorization: `Bearer ${token}` } : base
}
function handleUnauthorized(res) {
  if (res.status === 401 && getToken() && onUnauthorized) onUnauthorized()
}

const post = (url, body, timeoutMs) => request(url, { method: 'POST', body: JSON.stringify(body), timeoutMs })

// ============ 账号 ============
export const register = (email, password, nickname = '') => post(`${BASE}/auth/register`, { email, password, nickname })
export const login = (email, password) => post(`${BASE}/auth/login`, { email, password })
export const registerPhone = (phone, password, nickname = '') => post(`${BASE}/auth/register/phone`, { phone, password, nickname })
export const loginPhone = (phone, password) => post(`${BASE}/auth/login/phone`, { phone, password })
export const fetchMe = () => request(`${BASE}/auth/me`)
export const updateMe = (payload) => request(`${BASE}/auth/me`, { method: 'PUT', body: JSON.stringify(payload) })
export const deleteMe = () => request(`${BASE}/auth/me`, { method: 'DELETE' })

// ============ 简历 / JD ============
const AI_TIMEOUT = 90000
export const analyzeJD = (jd_text) => post(`${BASE}/resume/jd/analyze`, { jd_text })
export const generateResume = (profile, jd_text, template = 'modern', use_ai = true) =>
  post(`${BASE}/resume/generate`, { profile, jd_text, template, use_ai }, AI_TIMEOUT)
export const matchResume = (resume, jd_text) => post(`${BASE}/resume/match`, { resume, jd_text })
export const diagnoseResume = (resume, jd_text) => post(`${BASE}/resume/diagnose`, { resume, jd_text })
export const rewriteStar = (text, jd_text = '', use_ai = true) =>
  post(`${BASE}/resume/rewrite`, { text, jd_text, use_ai }, AI_TIMEOUT)
export const coverLetter = (resume, jd_text, use_ai = true) =>
  post(`${BASE}/resume/cover-letter`, { resume, jd_text, use_ai }, AI_TIMEOUT)
export const interviewQuestions = (resume, jd_text, use_ai = true) =>
  post(`${BASE}/resume/interview-questions`, { resume, jd_text, use_ai }, AI_TIMEOUT)

export const listSavedResumes = () => request(`${BASE}/resume/saved`)
export const saveResume = (payload) => post(`${BASE}/resume/saved`, payload)
export const getSavedResume = (id) => request(`${BASE}/resume/saved/${encodeURIComponent(id)}`)
export const deleteSavedResume = (id) => request(`${BASE}/resume/saved/${encodeURIComponent(id)}`, { method: 'DELETE' })

// ============ 求职看板 ============
export const listJobs = () => request(`${BASE}/jobs`)
export const createJob = (payload) => post(`${BASE}/jobs`, payload)
export const updateJob = (id, payload) => request(`${BASE}/jobs/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify(payload) })
export const deleteJob = (id) => request(`${BASE}/jobs/${encodeURIComponent(id)}`, { method: 'DELETE' })

// ============ 面试会话 ============
export function createSession(direction, role, positionDescription = '') {
  const query = new URLSearchParams({ direction, role })
  if (positionDescription) query.set('position_description', positionDescription.slice(0, 600))
  return request(`${BASE}/interview/sessions?${query}`, { method: 'POST' })
}

export function deleteSession(sessionId) {
  return request(`${BASE}/interview/sessions/${encodeURIComponent(sessionId)}`, { method: 'DELETE' })
}

// ============ 岗位目录 ============
export function listPositions(category = null, keyword = '') {
  const query = new URLSearchParams()
  if (category) query.set('category', category)
  if (keyword) query.set('keyword', keyword)
  const qs = query.toString()
  return request(`${BASE}/positions${qs ? `?${qs}` : ''}`)
}

export function getPosition(id) {
  return request(`${BASE}/positions/${encodeURIComponent(id)}`)
}

// ============ 面试题库 ============
function toQuery(params = {}) {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([k, v]) => {
    if (v !== null && v !== undefined && v !== '' && v !== false) query.set(k, String(v))
  })
  const qs = query.toString()
  return qs ? `?${qs}` : ''
}

export function listQuestions(params = {}) {
  return request(`${BASE}/questions${toQuery(params)}`)
}

export function getQuestionsMeta() {
  return request(`${BASE}/questions/meta`)
}

export function randomQuestions(params = {}) {
  return request(`${BASE}/questions/random${toQuery(params)}`)
}

export function getQuestion(id) {
  return request(`${BASE}/questions/${encodeURIComponent(id)}`)
}

export function setFavorite(id, favorite) {
  return request(`${BASE}/questions/${encodeURIComponent(id)}/favorite`, { method: 'PUT', body: JSON.stringify({ favorite }) })
}

export function addPractice(id, { answer, self_rating = null }) {
  return request(`${BASE}/questions/${encodeURIComponent(id)}/practices`, { method: 'POST', body: JSON.stringify({ answer, self_rating }) })
}

export function listPractices(limit = 50) {
  return request(`${BASE}/questions/practices?limit=${limit}`)
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
  const controller = new AbortController()
  const deadline = setTimeout(() => controller.abort(), 65000)
  let idle = null
  const resetIdle = () => {
    clearTimeout(idle)
    idle = setTimeout(() => controller.abort(), 22000)
  }
  try {
    resetIdle()
    const res = await fetch(`${CHAT_BASE}/chat/stream`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify(payload),
      signal: controller.signal
    })
    handleUnauthorized(res)
    if (!res.ok) throw new Error(await readErrorMessage(res))
    if (!res.body) throw new Error('对话服务暂时不可用')
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let finished = false
    while (!finished) {
      const { done, value } = await reader.read()
      if (done) break
      resetIdle()
      buffer += decoder.decode(value, { stream: true })
      const blocks = buffer.split(/\r?\n\r?\n/)
      buffer = blocks.pop()
      for (const block of blocks) {
        let event = 'message'
        let data = ''
        for (const line of block.split(/\r?\n/)) {
          if (line.startsWith('event:')) event = line.slice(6).trim()
          else if (line.startsWith('data:')) data += line.slice(5).trim()
        }
        if (!data) continue
        let parsed
        try { parsed = JSON.parse(data) } catch { continue }
        if (event === 'error') throw new Error(parsed.message || '对话暂时中断')
        if (event === 'meta') onMeta?.(parsed)
        else if (event === 'profile') onProfile?.(parsed)
        else if (event === 'done') { finished = true; await onDone?.(parsed); break }
        else if (parsed.content) onChunk?.(parsed.content, parsed)
      }
    }
    if (!finished) throw new Error('对话连接中断')
  } catch (err) {
    onError?.(err)
  } finally {
    clearTimeout(deadline)
    clearTimeout(idle)
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
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ text }),
    signal: AbortSignal.timeout(8000)
  })
  handleUnauthorized(res)
  if (!res.ok || res.status === 204) throw new Error('语音暂不可用')
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
    headers: authHeaders(),
    body: formData
  })
  handleUnauthorized(res)
  if (!res.ok) throw new Error(await readErrorMessage(res))
  try {
    const data = await res.json()
    return data.text || ''
  } catch {
    throw new Error('语音识别暂时不可用,请稍后重试')
  }
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
    timeoutMs: 60000,
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
  return request(`${BASE}/knowledge/upload`, { method: 'POST', body: formData, timeoutMs: 45000 })
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
