<script setup>
import { ref, onMounted, computed } from 'vue'
import { useKnowledgeStore } from '../stores/knowledge'
import { useChatStore } from '../stores/chat'

const kb = useKnowledgeStore()
const chat = useChatStore()
const documentType = ref('other')
const redact = ref(true)
const retentionDays = ref(30)
const profileLoading = ref(false)
const privacyLoading = ref(false)
const sessionId = computed(() => chat.sessionId)
const query = ref('')
const dragOver = ref(false)

// 已上传文件列表
const files = ref([])
const loadingFiles = ref(false)
const deletingSource = ref('')

async function loadFiles() {
  loadingFiles.value = true
  try {
    files.value = await kb.loadFiles(sessionId.value)
  } catch (e) {
    files.value = []
  } finally {
    loadingFiles.value = false
  }
}

async function onFileChange(e) {
  const files = e.target.files
  if (!files.length) return
  await kb.upload(files[0], { documentType: documentType.value, sessionId: sessionId.value, retentionDays: retentionDays.value, redact: redact.value })
  e.target.value = ''
  // 上传后刷新文件列表
  if (kb.uploadResult) await loadFiles()
}

async function onDrop(e) {
  e.preventDefault()
  dragOver.value = false
  const file = e.dataTransfer.files[0]
  if (file) {
    await kb.upload(file, { documentType: documentType.value, sessionId: sessionId.value, retentionDays: retentionDays.value, redact: redact.value })
    if (kb.uploadResult) await loadFiles()
  }
}

async function onSearch() {
  if (!query.value.trim()) return
  await kb.search(query.value)
}

async function onDelete(file) {
  if (!confirm(`确认删除「${file.source}」的所有片段?此操作不可恢复。`)) return
  deletingSource.value = file.document_id
  try {
    await kb.remove(file.document_id)
    await loadFiles()
  } catch (e) {
    alert(`删除失败:${e.message}`)
  } finally {
    deletingSource.value = ''
  }
}

async function generateProfile() {
  if (!sessionId.value) {
    alert('请先在面试间创建会话，再生成岗位画像。')
    return
  }
  profileLoading.value = true
  try { await kb.generate(sessionId.value) } catch (e) { alert(`画像生成失败:${e.message}`) } finally { profileLoading.value = false }
}

async function clearData() {
  if (!confirm('确认清空所有个人资料、会话与评估数据？此操作不可恢复。')) return
  privacyLoading.value = true
  try { await kb.clearAll(); files.value = []; chat.reset() } catch (e) { alert(`清空失败:${e.message}`) } finally { privacyLoading.value = false }
}

function fileIcon(name) {
  const ext = (name || '').split('.').pop().toLowerCase()
  if (ext === 'pdf') return '📕'
  if (['doc', 'docx'].includes(ext)) return '📘'
  if (ext === 'md') return '📝'
  return '📄'
}

// 总片段数
const totalChunks = () => files.value.reduce((s, f) => s + f.chunks, 0)

onMounted(() => {
  loadFiles()
})
</script>

<template>
  <div class="kb-page">
    <div class="page-title">个人资料库</div>
    <div class="page-sub">上传简历、面经、笔记,Agent 会基于你的真实经历提问与评估</div>

    <!-- 上传区 -->
    <div
      class="card upload-zone"
      :class="{ drag: dragOver }"
      @dragover.prevent="dragOver = true"
      @dragleave="dragOver = false"
      @drop="onDrop"
    >
      <div class="upload-icon">📎</div>
      <div class="upload-text">
        <strong>点击或拖拽文件到此处上传</strong>
        <div class="text-soft text-sm mt-2">支持 PDF / Word / TXT / Markdown</div>
      </div>
      <div class="upload-options">
        <select v-model="documentType" class="select">
          <option value="resume">简历</option><option value="candidate">候选人资料</option><option value="job_description">JD</option><option value="company">企业介绍</option><option value="other">其他</option>
        </select>
        <label class="text-soft text-sm"><input v-model="redact" type="checkbox" /> 自动脱敏</label>
        <label class="text-soft text-sm">保留 <input v-model.number="retentionDays" class="days-input" type="number" min="1" max="3650" /> 天</label>
      </div>
      <label class="btn btn-primary">
        选择文件
        <input type="file" accept=".pdf,.docx,.doc,.txt,.md" hidden @change="onFileChange" />
      </label>
    </div>

    <!-- 上传结果 -->
    <div v-if="kb.uploading" class="card status">⏳ 正在解析并向量化…</div>
    <div v-if="kb.uploadResult" class="card status success">
      ✅ {{ kb.uploadResult.message }}
      <span class="text-soft text-sm">
        ({{ kb.uploadResult.filename }} · {{ kb.uploadResult.chunks }} 片段)
      </span>
    </div>

    <!-- 已上传文件列表 -->
    <div class="card">
      <div class="section-head">
        <div class="section-title">已上传文件</div>
        <span v-if="files.length" class="text-soft text-sm">
          共 {{ files.length }} 个文件 · {{ totalChunks() }} 个片段
        </span>
        <button class="btn btn-ghost btn-sm" @click="loadFiles" :disabled="loadingFiles">
          {{ loadingFiles ? '刷新中…' : '↻ 刷新' }}
        </button>
      </div>

      <div v-if="files.length" class="file-list">
        <div v-for="f in files" :key="f.document_id" class="file-item">
          <span class="file-icon">{{ fileIcon(f.source) }}</span>
          <span class="file-name" :title="f.source">{{ f.source }}</span>
          <span class="tag">{{ ({ resume: '简历', job_description: 'JD', company: '企业介绍', other: '其他' }[f.document_type] || f.document_type) }}</span>
          <span class="tag">ID {{ f.document_id }}</span>
          <span class="file-chunks tag">{{ f.chunks }} 片段</span>
          <button
            class="btn-del"
            @click="onDelete(f)"
            :disabled="deletingSource === f.document_id"
            title="删除"
          >
            {{ deletingSource === f.document_id ? '…' : '✕' }}
          </button>
        </div>
      </div>
      <div v-else-if="!loadingFiles" class="empty-hint text-soft text-sm">
        还没有上传文件,Agent 将无法基于个人资料提问
      </div>
    </div>

    <div class="card profile-section">
      <div class="section-head"><div class="section-title">岗位与能力画像</div><button class="btn btn-primary btn-sm" @click="generateProfile" :disabled="profileLoading">{{ profileLoading ? '生成中…' : '生成画像' }}</button></div>
      <div v-if="kb.profile" class="profile-grid">
        <div><b>岗位匹配度</b><strong class="match-score">{{ kb.profile.match_score }}%</strong></div>
        <div><b>候选人优势</b><p>{{ kb.profile.candidate_strengths?.join('、') || '暂无' }}</p></div>
        <div><b>能力缺口</b><p>{{ kb.profile.requirement_gaps?.join('、') || '暂无' }}</p></div>
        <div><b>重点考察</b><p>{{ kb.profile.focus_areas?.join('、') || '暂无' }}</p></div>
        <div><b>问题计划</b><p>{{ kb.profile.interview_plan?.join('；') || '暂无' }}</p></div>
      </div><div v-else class="text-soft text-sm">绑定会话后可生成岗位、候选人与企业画像。</div>
    </div>
    <div class="card privacy-card">
      <div class="section-title">隐私与数据管理</div>
      <p class="text-soft text-sm">资料仅用于面试检索、岗位画像与评估；默认自动脱敏，保留期结束后自动清理。当前状态：{{ redact ? '上传时自动脱敏' : '未脱敏' }}。配置模型后，相关片段和对话才会发送到模型网关。</p>
      <button class="btn btn-ghost btn-sm" @click="clearData" :disabled="privacyLoading">{{ privacyLoading ? '清理中…' : '清空个人数据' }}</button>
    </div>

    <!-- 检索测试 -->
    <div class="card">
      <div class="section-title">检索测试</div>
      <p class="text-soft text-sm" style="margin-bottom: 12px">
        输入问题,测试 Agent 能从你的资料中检索到哪些相关内容
      </p>
      <div class="search-row">
        <input v-model="query" class="input" placeholder="例如:我在 RAG 项目里用了什么向量库?" @keydown.enter="onSearch" />
        <button class="btn btn-primary" @click="onSearch" :disabled="kb.retrieving">
          {{ kb.retrieving ? '检索中…' : '检索' }}
        </button>
      </div>

      <div v-if="kb.searchResults.length" class="results">
        <div v-for="(d, i) in kb.searchResults" :key="i" class="result-item">
          <div class="result-head">
            <span class="tag tag-primary">{{ d.source }}</span>
            <span class="text-soft text-sm">相关度 {{ (d.score * 100).toFixed(0) }}%</span>
          </div>
          <div class="result-content">{{ d.content }}</div>
        </div>
      </div>
      <div v-else-if="query && !kb.retrieving" class="text-soft text-sm mt-4">
        暂无检索结果。请先上传资料,或确认已配置 Embedding API Key。
      </div>
    </div>
  </div>
</template>

<style scoped>
.kb-page {
  max-width: 860px;
  margin: 0 auto;
}
.upload-zone {
  display: flex;
  align-items: center;
  gap: 18px;
  border: 2px dashed var(--border);
  text-align: center;
  transition: border-color 0.2s, background 0.2s;
  margin-bottom: 16px;
}
.upload-zone.drag {
  border-color: var(--primary);
  background: rgba(79, 70, 229, 0.08);
}
.upload-icon {
  font-size: 36px;
}
.upload-text {
  flex: 1;
  text-align: left;
}
.upload-options { display: grid; gap: 6px; min-width: 150px; }
.days-input { width: 55px; padding: 3px 5px; background: var(--bg); color: var(--text); border: 1px solid var(--border); border-radius: 6px; }
.profile-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.profile-grid > div { padding: 10px; background: var(--bg); border-radius: var(--radius-sm); }
.profile-grid p { color: var(--text-soft); font-size: 13px; margin-top: 4px; }
.match-score { display: block; font-size: 28px; color: var(--success); }
.privacy-card { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.privacy-card .section-title { width: 100%; margin-bottom: 0; }
.privacy-card p { flex: 1; min-width: 220px; }
.upload-text strong {
  font-size: 15px;
}
.status {
  margin-bottom: 16px;
}
.status.success {
  border-color: var(--success);
}
.section-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.section-head .section-title {
  margin-bottom: 0;
  flex: 1;
}
.section-title {
  font-weight: 700;
  font-size: 16px;
  margin-bottom: 6px;
}
.btn-sm {
  padding: 5px 12px;
  font-size: 13px;
}
.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  transition: border-color 0.15s;
}
.file-item:hover {
  border-color: var(--primary);
}
.file-icon {
  font-size: 20px;
  flex-shrink: 0;
}
.file-name {
  flex: 1;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.file-chunks {
  flex-shrink: 0;
}
.btn-del {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--text-soft);
  border-radius: 50%;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.15s, color 0.15s;
}
.btn-del:hover:not(:disabled) {
  background: var(--danger);
  color: #fff;
}
.btn-del:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.empty-hint {
  text-align: center;
  padding: 24px 0;
}
.search-row {
  display: flex;
  gap: 10px;
}
.results {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.result-item {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 14px;
}
.result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.result-content {
  font-size: 14px;
  line-height: 1.7;
  color: var(--text-soft);
  white-space: pre-wrap;
}

@media (max-width: 768px) {
  .upload-zone {
    flex-direction: column;
    text-align: center;
  }
  .upload-text {
    text-align: center;
  }
  .upload-options { width: 100%; }
  .profile-grid { grid-template-columns: 1fr; }
  .search-row {
    flex-direction: column;
  }
}
</style>
