<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useKnowledgeStore } from '../stores/knowledge'
import { useChatStore } from '../stores/chat'
import { toast } from '../utils/toast'
import Icon from '../components/Icon.vue'

const router = useRouter()
const kb = useKnowledgeStore()
const chat = useChatStore()

const DOC_TYPES = [
  { id: 'resume', name: '简历', icon: 'user', desc: '让面试官围绕真实经历深挖' },
  { id: 'job_description', name: '岗位 JD', icon: 'briefcase', desc: '对齐岗位要求与考察重点' },
  { id: 'company', name: '企业介绍', icon: 'layers', desc: '业务背景与公司文化' },
  { id: 'candidate', name: '候选人资料', icon: 'fileText', desc: '作品集、项目复盘等' },
  { id: 'other', name: '其他', icon: 'file', desc: '面经、笔记、学习资料' }
]
const DOC_NAMES = Object.fromEntries(DOC_TYPES.map((d) => [d.id, d.name]))
const ACCEPT = ['pdf', 'docx', 'doc', 'txt', 'md']
const MAX_MB = 20

const documentType = ref('resume')
const redact = ref(true)
const retentionDays = ref(30)
const dragOver = ref(false)
const fileInput = ref(null)

const files = ref([])
const loadingFiles = ref(false)
const deletingId = ref('')
const typeFilter = ref('all')

const query = ref('')
const searched = ref(false)
const profileLoading = ref(false)
const privacyLoading = ref(false)
const retentionSaving = ref(false)

const sessionId = computed(() => chat.sessionId)
const totalChunks = computed(() => files.value.reduce((s, f) => s + (f.chunks || 0), 0))
const typeCounts = computed(() => files.value.reduce((acc, f) => {
  acc[f.document_type] = (acc[f.document_type] || 0) + 1
  return acc
}, {}))
const visibleFiles = computed(() => typeFilter.value === 'all' ? files.value : files.value.filter((f) => f.document_type === typeFilter.value))
const hasResume = computed(() => Boolean(typeCounts.value.resume))
const hasJD = computed(() => Boolean(typeCounts.value.job_description))
const readiness = computed(() => {
  let score = 0
  if (hasResume.value) score += 50
  if (hasJD.value) score += 35
  if (typeCounts.value.company) score += 15
  return score
})

function fileIcon(name) {
  const ext = (name || '').split('.').pop().toLowerCase()
  if (ext === 'pdf') return 'fileText'
  if (ext === 'md') return 'hash'
  return 'file'
}
function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
function daysLeft(iso) {
  if (!iso) return null
  const diff = Math.ceil((new Date(iso).getTime() - Date.now()) / 86400000)
  return Number.isFinite(diff) ? Math.max(0, diff) : null
}

async function loadFiles() {
  loadingFiles.value = true
  try {
    files.value = await kb.loadFiles(sessionId.value)
  } catch (e) {
    files.value = []
    toast(e.message || '文件列表加载失败', 'danger')
  } finally {
    loadingFiles.value = false
  }
}

async function loadSessionExtras() {
  if (!sessionId.value) return
  await Promise.all([
    kb.loadProfiles(sessionId.value).catch(() => {}),
    kb.loadPrivacy(sessionId.value).then((p) => { if (p?.retention_days) retentionDays.value = p.retention_days }).catch(() => {})
  ])
}

function validate(file) {
  const ext = (file.name || '').split('.').pop().toLowerCase()
  if (!ACCEPT.includes(ext)) return `不支持 .${ext} 格式，请上传 PDF / Word / TXT / Markdown`
  if (file.size > MAX_MB * 1024 * 1024) return `文件超过 ${MAX_MB}MB`
  return ''
}

async function doUpload(file) {
  if (!file || kb.uploading) return
  const err = validate(file)
  if (err) { toast(err, 'warning'); return }
  const days = Math.min(3650, Math.max(1, Number(retentionDays.value) || 30))
  try {
    const result = await kb.upload(file, { documentType: documentType.value, sessionId: sessionId.value, retentionDays: days, redact: redact.value })
    toast(`${result?.filename || file.name} 已解析，共 ${result?.chunks ?? 0} 个片段`, 'success')
    await loadFiles()
  } catch (e) {
    toast(e.message || '上传失败', 'danger')
  }
}

function onFileChange(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  doUpload(file)
}
function onDrop(e) {
  dragOver.value = false
  doUpload(e.dataTransfer?.files?.[0])
}

async function onDelete(file) {
  if (!confirm(`确认删除「${file.source}」及其全部片段？此操作不可恢复。`)) return
  deletingId.value = file.document_id
  try {
    await kb.remove(file.document_id)
    files.value = files.value.filter((f) => f.document_id !== file.document_id)
    toast('已删除', 'success')
  } catch (e) {
    toast(`删除失败：${e.message}`, 'danger')
  } finally {
    deletingId.value = ''
  }
}

async function onSearch() {
  const q = query.value.trim()
  if (!q) return
  try {
    await kb.search(q, 4, sessionId.value)
  } catch (e) {
    toast(e.message || '检索失败', 'danger')
  } finally {
    searched.value = true
  }
}

async function onGenerateProfile() {
  if (!sessionId.value) {
    toast('请先在面试间开始一场面试，再生成岗位画像', 'warning')
    return
  }
  profileLoading.value = true
  try {
    await kb.generate(sessionId.value)
    toast('画像已更新', 'success')
  } catch (e) {
    toast(`画像生成失败：${e.message}`, 'danger')
  } finally {
    profileLoading.value = false
  }
}

async function saveRetention() {
  if (!sessionId.value) return
  const days = Math.min(3650, Math.max(1, Number(retentionDays.value) || 30))
  retentionDays.value = days
  retentionSaving.value = true
  try {
    await kb.setRetention(sessionId.value, days)
    toast(`保留期已设置为 ${days} 天`, 'success')
  } catch (e) {
    toast(e.message || '保存失败', 'danger')
  } finally {
    retentionSaving.value = false
  }
}

async function clearData() {
  if (!confirm('确认清空所有个人资料、会话与评估数据？此操作不可恢复。')) return
  privacyLoading.value = true
  try {
    await kb.clearAll()
    files.value = []
    kb.searchResults = []
    chat.reset()
    toast('个人数据已全部清空', 'success')
  } catch (e) {
    toast(`清空失败：${e.message}`, 'danger')
  } finally {
    privacyLoading.value = false
  }
}

onMounted(() => {
  loadFiles()
  loadSessionExtras()
})
</script>

<template>
  <div class="container kb-page">
    <header class="page-head">
      <div>
        <div class="eyebrow">Knowledge Base</div>
        <h1 class="page-title">个人资料库</h1>
        <p class="page-sub">上传简历、JD 与企业资料，面试官会基于你的真实经历提问，评估也会引用原文作为依据</p>
      </div>
      <button class="btn btn-gradient" @click="router.push('/chat')"><Icon name="play" :size="16" /> 开始面试</button>
    </header>

    <div v-if="!sessionId" class="alert alert-info">
      <Icon class="alert-icon" name="info" :size="18" />
      <div class="flex-1">当前未绑定面试会话，资料将作为全局资料使用。开始一场面试后上传，可生成专属的岗位匹配画像。</div>
    </div>

    <!-- 统计 -->
    <section class="grid-4">
      <div class="card stat">
        <div class="stat-label">已上传文件</div>
        <div class="stat-value">{{ files.length }}</div>
        <div class="stat-foot">共 {{ totalChunks }} 个检索片段</div>
      </div>
      <div class="card stat">
        <div class="stat-label">简历</div>
        <div class="stat-value" :class="hasResume ? 'text-success' : 'text-dim'">{{ typeCounts.resume || 0 }}</div>
        <div class="stat-foot">{{ hasResume ? '已就绪' : '建议上传' }}</div>
      </div>
      <div class="card stat">
        <div class="stat-label">岗位 JD</div>
        <div class="stat-value" :class="hasJD ? 'text-success' : 'text-dim'">{{ typeCounts.job_description || 0 }}</div>
        <div class="stat-foot">{{ hasJD ? '已就绪' : '建议上传' }}</div>
      </div>
      <div class="card stat">
        <div class="stat-label">资料完整度</div>
        <div class="stat-value">{{ readiness }}<small>%</small></div>
        <div class="progress mt-2"><span :style="{ width: readiness + '%' }"></span></div>
      </div>
    </section>

    <div class="layout">
      <div class="stack gap-4">
        <!-- 上传 -->
        <section class="card">
          <div class="section-title"><Icon name="upload" :size="18" /> 上传资料</div>
          <div class="type-grid">
            <button v-for="t in DOC_TYPES" :key="t.id" type="button" class="type-card" :class="{ active: documentType === t.id }"
              :aria-pressed="documentType === t.id" @click="documentType = t.id">
              <Icon :name="t.icon" :size="18" />
              <strong>{{ t.name }}</strong>
              <span class="text-xs text-soft">{{ t.desc }}</span>
            </button>
          </div>

          <div class="dropzone mt-4" :class="{ drag: dragOver, busy: kb.uploading }" role="button" tabindex="0"
            aria-label="点击或拖拽文件上传"
            @click="fileInput?.click()" @keydown.enter.prevent="fileInput?.click()" @keydown.space.prevent="fileInput?.click()"
            @dragover.prevent="dragOver = true" @dragleave.prevent="dragOver = false" @drop.prevent="onDrop">
            <template v-if="kb.uploading">
              <div class="spinner"></div>
              <strong class="mt-2">正在解析、脱敏并建立索引…</strong>
            </template>
            <template v-else>
              <div class="drop-icon"><Icon name="upload" :size="24" /></div>
              <strong>点击或拖拽文件到此处</strong>
              <span class="text-sm text-soft">将作为「{{ DOC_NAMES[documentType] }}」上传 · 支持 PDF / Word / TXT / Markdown，最大 {{ MAX_MB }}MB</span>
            </template>
            <input ref="fileInput" type="file" :accept="ACCEPT.map((e) => '.' + e).join(',')" hidden @change="onFileChange" />
          </div>

          <div class="row gap-4 wrap mt-4">
            <div class="row gap-2 text-sm">
              <label class="switch">
                <input v-model="redact" type="checkbox" />
                <span></span>
              </label>
              <span>自动脱敏（手机号、邮箱、身份证等）</span>
            </div>
            <label class="row gap-2 text-sm text-soft">
              保留
              <input v-model.number="retentionDays" class="input days-input" type="number" min="1" max="3650" />
              天
            </label>
          </div>
        </section>

        <!-- 文件列表 -->
        <section class="card">
          <div class="row mb-4">
            <div class="section-title" style="margin: 0"><Icon name="folder" :size="18" /> 已上传文件</div>
            <button class="btn btn-ghost btn-sm ml-auto" :disabled="loadingFiles" @click="loadFiles">
              <Icon name="refresh" :size="14" /> 刷新
            </button>
          </div>
          <div v-if="files.length" class="row gap-2 wrap mb-4">
            <button class="chip" :class="{ active: typeFilter === 'all' }" @click="typeFilter = 'all'">全部 <span class="count">{{ files.length }}</span></button>
            <template v-for="t in DOC_TYPES" :key="t.id">
              <button v-if="typeCounts[t.id]" class="chip" :class="{ active: typeFilter === t.id }" @click="typeFilter = t.id">
                {{ t.name }} <span class="count">{{ typeCounts[t.id] }}</span>
              </button>
            </template>
          </div>

          <div v-if="loadingFiles && !files.length" class="stack gap-2">
            <div v-for="i in 3" :key="i" class="skeleton" style="height: 56px"></div>
          </div>
          <div v-else-if="visibleFiles.length" class="file-list">
            <div v-for="f in visibleFiles" :key="f.document_id" class="file-item">
              <div class="file-icon"><Icon :name="fileIcon(f.source)" :size="18" /></div>
              <div class="flex-1" style="min-width: 0">
                <div class="truncate file-name" :title="f.source">{{ f.source }}</div>
                <div class="row gap-2 wrap text-xs text-soft mt-1">
                  <span class="tag tag-primary">{{ DOC_NAMES[f.document_type] || f.document_type }}</span>
                  <span>{{ f.chunks || 0 }} 片段</span>
                  <span>上传于 {{ formatDate(f.created_at) }}</span>
                  <span v-if="f.redacted" class="text-success"><Icon name="shield" :size="12" /> 已脱敏 {{ f.redaction_count || 0 }} 处</span>
                  <span v-if="daysLeft(f.expires_at) !== null"><Icon name="clock" :size="12" /> {{ daysLeft(f.expires_at) }} 天后清理</span>
                </div>
              </div>
              <button class="btn btn-icon btn-ghost btn-sm" :disabled="deletingId === f.document_id"
                :aria-label="`删除 ${f.source}`" title="删除" @click="onDelete(f)">
                <span v-if="deletingId === f.document_id" class="spinner"></span>
                <Icon v-else name="trash" :size="16" />
              </button>
            </div>
          </div>
          <div v-else class="empty">
            <div class="empty-icon"><Icon name="folder" :size="28" /></div>
            <div class="empty-title">还没有资料</div>
            <div class="empty-desc">上传简历后，面试官会围绕你的项目经历追问，回答更贴近真实面试</div>
          </div>
        </section>

        <!-- 检索测试 -->
        <section class="card">
          <div class="section-title"><Icon name="search" :size="18" /> 检索测试</div>
          <p class="text-soft text-sm mb-4">输入问题，查看面试官能从你的资料中检索到哪些内容</p>
          <form class="row gap-2" @submit.prevent="onSearch">
            <div class="input-group flex-1">
              <Icon class="icon-lead" name="search" :size="16" />
              <input v-model="query" class="input" maxlength="200" placeholder="例如：我在 RAG 项目里用了什么向量库？" aria-label="检索内容" />
            </div>
            <button class="btn btn-primary" type="submit" :disabled="kb.retrieving || !query.trim()">
              <span v-if="kb.retrieving" class="spinner"></span>
              {{ kb.retrieving ? '检索中' : '检索' }}
            </button>
          </form>
          <div v-if="kb.searchResults.length" class="stack gap-2 mt-4">
            <article v-for="(d, i) in kb.searchResults" :key="d.chunk_id || i" class="result">
              <div class="row gap-2 wrap">
                <span class="tag tag-primary"><Icon name="file" :size="12" /> {{ d.source || '资料' }}</span>
                <span v-if="d.document_type" class="tag">{{ DOC_NAMES[d.document_type] || d.document_type }}</span>
                <span v-if="d.page" class="text-xs text-soft">第 {{ d.page }} 页</span>
                <span class="text-xs text-soft ml-auto">相关度 {{ Math.round((d.score || 0) * 100) }}%</span>
              </div>
              <div class="progress mt-2 thin"><span :style="{ width: Math.round((d.score || 0) * 100) + '%' }"></span></div>
              <p class="result-content">{{ d.content || d.excerpt }}</p>
            </article>
          </div>
          <div v-else-if="searched && !kb.retrieving" class="empty compact mt-4">
            <div class="empty-desc">没有检索到相关内容。可以换个说法，或先上传相关资料。</div>
          </div>
        </section>
      </div>

      <aside class="stack gap-4">
        <!-- 画像 -->
        <section class="card">
          <div class="row mb-4">
            <div class="section-title" style="margin: 0"><Icon name="target" :size="18" /> 岗位匹配画像</div>
          </div>
          <template v-if="kb.profile">
            <div class="match">
              <div class="match-num">{{ Math.round(kb.profile.match_score || 0) }}<small>%</small></div>
              <div class="text-sm text-soft">岗位匹配度</div>
              <div class="progress mt-2"><span :style="{ width: (kb.profile.match_score || 0) + '%' }"></span></div>
            </div>
            <div class="profile-block">
              <div class="pb-title text-success"><Icon name="checkCircle" :size="14" /> 候选人优势</div>
              <div class="row gap-2 wrap">
                <span v-for="s in kb.profile.candidate_strengths || []" :key="s" class="tag tag-success">{{ s }}</span>
                <span v-if="!kb.profile.candidate_strengths?.length" class="text-dim text-sm">暂无</span>
              </div>
            </div>
            <div class="profile-block">
              <div class="pb-title text-danger"><Icon name="alert" :size="14" /> 能力缺口</div>
              <div class="row gap-2 wrap">
                <span v-for="s in kb.profile.requirement_gaps || []" :key="s" class="tag tag-danger">{{ s }}</span>
                <span v-if="!kb.profile.requirement_gaps?.length" class="text-dim text-sm">暂无</span>
              </div>
            </div>
            <div class="profile-block">
              <div class="pb-title text-primary"><Icon name="compass" :size="14" /> 重点考察</div>
              <div class="row gap-2 wrap">
                <span v-for="s in kb.profile.focus_areas || []" :key="s" class="tag">{{ s }}</span>
                <span v-if="!kb.profile.focus_areas?.length" class="text-dim text-sm">暂无</span>
              </div>
            </div>
            <div v-if="kb.profile.interview_plan?.length" class="profile-block">
              <div class="pb-title"><Icon name="list" :size="14" /> 提问计划</div>
              <ol class="plan">
                <li v-for="(p, i) in kb.profile.interview_plan" :key="i">{{ p }}</li>
              </ol>
            </div>
          </template>
          <div v-else class="empty compact">
            <div class="empty-icon"><Icon name="target" :size="24" /></div>
            <div class="empty-desc">{{ sessionId ? '上传简历与 JD 后生成画像，面试官会据此制定提问计划' : '开始一场面试后即可生成专属画像' }}</div>
          </div>
          <button class="btn btn-primary btn-block mt-4" :disabled="profileLoading || !sessionId" @click="onGenerateProfile">
            <span v-if="profileLoading" class="spinner"></span>
            <Icon v-else name="sparkles" :size="16" />
            {{ profileLoading ? '生成中…' : kb.profile ? '重新生成画像' : '生成画像' }}
          </button>
        </section>

        <!-- 隐私 -->
        <section class="card">
          <div class="section-title"><Icon name="shield" :size="18" /> 隐私与数据</div>
          <ul class="privacy-list text-sm text-soft">
            <li><Icon name="lock" :size="14" /> {{ kb.privacy?.purpose || '资料仅用于模拟面试检索、画像与评估' }}</li>
            <li><Icon name="database" :size="14" /> 存储：{{ kb.privacy?.storage || 'SQLite 与本地上传目录' }}</li>
            <li><Icon name="server" :size="14" /> {{ kb.privacy?.external_processing || '配置模型后，相关片段和对话才会发送到模型网关' }}</li>
            <li><Icon name="shield" :size="14" /> 上传时{{ redact ? '自动脱敏' : '不脱敏' }}</li>
          </ul>
          <div v-if="sessionId" class="row gap-2 mt-4">
            <span class="text-sm">本会话保留期</span>
            <input v-model.number="retentionDays" class="input days-input" type="number" min="1" max="3650" aria-label="保留天数" />
            <span class="text-sm text-soft">天</span>
            <button class="btn btn-secondary btn-sm ml-auto" :disabled="retentionSaving" @click="saveRetention">保存</button>
          </div>
          <button class="btn btn-danger btn-block mt-4" :disabled="privacyLoading" @click="clearData">
            <span v-if="privacyLoading" class="spinner"></span>
            <Icon v-else name="trash" :size="16" />
            {{ privacyLoading ? '清理中…' : '清空全部个人数据' }}
          </button>
        </section>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.kb-page { display: flex; flex-direction: column; gap: 16px; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 16px; align-items: start; }
.section-title { display: flex; align-items: center; gap: 8px; }
.stat-value small { font-size: 14px; color: var(--text-dim); margin-left: 2px; }

.type-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.type-card {
  display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 12px;
  border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg);
  color: var(--text); text-align: left; cursor: pointer; transition: border-color .15s, background .15s, transform .15s;
}
.type-card:hover { border-color: var(--primary); transform: translateY(-1px); }
.type-card.active { border-color: var(--primary); background: var(--info-bg); box-shadow: 0 0 0 3px var(--primary-glow); }
.type-card.active :deep(svg) { color: var(--primary); }

.dropzone {
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px;
  padding: 32px 16px; border: 2px dashed var(--border); border-radius: var(--radius); cursor: pointer;
  text-align: center; transition: border-color .2s, background .2s;
}
.dropzone:hover, .dropzone:focus-visible, .dropzone.drag { border-color: var(--primary); background: var(--info-bg); outline: none; }
.dropzone.busy { pointer-events: none; opacity: .8; }
.drop-icon { width: 52px; height: 52px; border-radius: 50%; display: flex; align-items: center; justify-content: center; background: var(--info-bg); color: var(--primary); margin-bottom: 4px; }
.days-input { width: 76px; padding: 6px 8px; }

.file-list { display: flex; flex-direction: column; gap: 8px; }
.file-item { display: flex; align-items: center; gap: 12px; padding: 12px 14px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg); transition: border-color .15s; }
.file-item:hover { border-color: var(--primary); }
.file-icon { width: 38px; height: 38px; flex-shrink: 0; border-radius: var(--radius-sm); display: flex; align-items: center; justify-content: center; background: var(--info-bg); color: var(--primary); }
.file-name { font-weight: 600; font-size: 14px; }

.result { padding: 14px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg); }
.result-content { margin: 10px 0 0; font-size: 14px; line-height: 1.7; color: var(--text-soft); white-space: pre-wrap; }
.progress.thin { height: 4px; }
.empty.compact { padding: 20px 8px; }

.match { text-align: center; padding: 8px 0 16px; border-bottom: 1px solid var(--border); }
.match-num { font-size: 44px; font-weight: 800; line-height: 1; color: var(--primary-soft); }
.match-num small { font-size: 16px; }
.profile-block { padding: 12px 0; border-bottom: 1px solid var(--border); }
.profile-block:last-of-type { border-bottom: none; }
.pb-title { display: flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.plan { margin: 0; padding-left: 18px; font-size: 13px; color: var(--text-soft); line-height: 1.7; }
.privacy-list { list-style: none; padding: 0; margin: 0; display: grid; gap: 8px; }
.privacy-list li { display: flex; gap: 8px; align-items: flex-start; line-height: 1.6; }
.privacy-list li :deep(svg) { flex-shrink: 0; margin-top: 3px; }

@media (max-width: 1100px) {
  .layout { grid-template-columns: 1fr; }
  .type-grid { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 768px) {
  .type-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
