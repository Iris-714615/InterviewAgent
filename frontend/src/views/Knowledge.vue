<script setup>
import { ref, onMounted } from 'vue'
import { useKnowledgeStore } from '../stores/knowledge'
import { listFiles, deleteFile } from '../api'

const kb = useKnowledgeStore()
const query = ref('')
const dragOver = ref(false)

// 已上传文件列表
const files = ref([])
const loadingFiles = ref(false)
const deletingSource = ref('')

async function loadFiles() {
  loadingFiles.value = true
  try {
    files.value = await listFiles()
  } catch (e) {
    files.value = []
  } finally {
    loadingFiles.value = false
  }
}

async function onFileChange(e) {
  const files = e.target.files
  if (!files.length) return
  await kb.upload(files[0])
  e.target.value = ''
  // 上传后刷新文件列表
  if (kb.uploadResult) await loadFiles()
}

async function onDrop(e) {
  e.preventDefault()
  dragOver.value = false
  const file = e.dataTransfer.files[0]
  if (file) {
    await kb.upload(file)
    if (kb.uploadResult) await loadFiles()
  }
}

async function onSearch() {
  if (!query.value.trim()) return
  await kb.search(query.value)
}

async function onDelete(source) {
  if (!confirm(`确认删除「${source}」的所有片段?此操作不可恢复。`)) return
  deletingSource.value = source
  try {
    await deleteFile(source)
    await loadFiles()
  } catch (e) {
    alert(`删除失败:${e.message}`)
  } finally {
    deletingSource.value = ''
  }
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
        <div v-for="f in files" :key="f.source" class="file-item">
          <span class="file-icon">{{ fileIcon(f.source) }}</span>
          <span class="file-name" :title="f.source">{{ f.source }}</span>
          <span class="file-chunks tag">{{ f.chunks }} 片段</span>
          <button
            class="btn-del"
            @click="onDelete(f.source)"
            :disabled="deletingSource === f.source"
            title="删除"
          >
            {{ deletingSource === f.source ? '…' : '✕' }}
          </button>
        </div>
      </div>
      <div v-else-if="!loadingFiles" class="empty-hint text-soft text-sm">
        还没有上传文件,Agent 将无法基于个人资料提问
      </div>
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
  .search-row {
    flex-direction: column;
  }
}
</style>
