<script setup>
import { computed, ref, onBeforeUnmount } from 'vue'
import { marked } from 'marked'
import { synthesizeTTS, modelBadge } from '../api'

const props = defineProps({
  role: { type: String, required: true }, // user | assistant
  content: { type: String, default: '' },
  coach: { type: Boolean, default: false }, // 是否教练消息
  streaming: { type: Boolean, default: false },
  model: { type: String, default: '' } // 本条回复使用的模型
})

marked.setOptions({ breaks: true })

const html = computed(() => {
  if (props.role === 'user') return props.content
  return marked.parse(props.content || '')
})

const isUser = computed(() => props.role === 'user')
const label = computed(() => {
  if (isUser.value) return '我'
  return props.coach ? '教练' : '面试官'
})
const avatar = computed(() => (isUser.value ? '🧑' : props.coach ? '🎓' : '🎤'))
const badge = computed(() => modelBadge(props.model))

// 语音播放状态
const ttsLoading = ref(false)
const ttsPlaying = ref(false)
const ttsError = ref('')
let audioEl = null
let audioUrl = null

const canPlay = computed(() => !isUser.value && props.content && !props.streaming)

async function toggleTTS() {
  // 正在播放则停止
  if (ttsPlaying.value && audioEl) {
    audioEl.pause()
    return
  }
  if (ttsLoading.value) return
  ttsError.value = ''
  ttsLoading.value = true
  try {
    if (audioUrl) URL.revokeObjectURL(audioUrl)
    audioUrl = await synthesizeTTS(props.content)
    audioEl = new Audio(audioUrl)
    audioEl.onended = () => { ttsPlaying.value = false }
    audioEl.onpause = () => { ttsPlaying.value = false }
    await audioEl.play()
    ttsPlaying.value = true
  } catch (e) {
    ttsError.value = e.message || '合成失败'
  } finally {
    ttsLoading.value = false
  }
}

onBeforeUnmount(() => {
  if (audioEl) { audioEl.pause(); audioEl = null }
  if (audioUrl) { URL.revokeObjectURL(audioUrl); audioUrl = null }
})
</script>

<template>
  <div class="msg" :class="{ user: isUser, coach: coach && !isUser }">
    <div class="avatar">{{ avatar }}</div>
    <div class="bubble-wrap">
      <div class="label">
        {{ label }}
        <span v-if="badge" class="model-badge" :class="badge" :title="'使用模型:' + model">{{ badge }}</span>
        <span v-if="streaming" class="typing">·输入中</span>
      </div>
      <div class="bubble" :class="{ md: !isUser }" v-html="html"></div>
      <div v-if="canPlay" class="msg-actions">
        <button class="tts-btn" :disabled="ttsLoading" @click="toggleTTS">
          <span v-if="ttsLoading">合成中…</span>
          <span v-else-if="ttsPlaying">⏸ 停止</span>
          <span v-else>🔊 朗读</span>
        </button>
        <span v-if="ttsError" class="tts-err">{{ ttsError }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.msg {
  display: flex;
  gap: 12px;
  max-width: 860px;
  margin: 0 auto 20px;
  animation: fadeInUp 0.3s ease;
}
.msg.user {
  flex-direction: row-reverse;
}
.avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--bg-hover);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 19px;
  flex-shrink: 0;
  border: 1px solid var(--border);
}
.msg.user .avatar {
  background: rgba(99, 102, 241, 0.15);
  border-color: rgba(99, 102, 241, 0.3);
}
.msg.coach .avatar {
  background: rgba(251, 191, 36, 0.15);
  border-color: rgba(251, 191, 36, 0.3);
}
.bubble-wrap {
  display: flex;
  flex-direction: column;
  max-width: 78%;
}
.msg.user .bubble-wrap {
  align-items: flex-end;
}
.label {
  font-size: 12px;
  color: var(--text-dim);
  margin-bottom: 5px;
  padding: 0 4px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.typing {
  color: var(--primary-soft);
  margin-left: 4px;
}
.model-badge {
  font-size: 10px;
  padding: 1px 7px;
  border-radius: var(--radius-pill);
  font-weight: 600;
  letter-spacing: 0.3px;
  line-height: 1.6;
}
.model-badge.flash {
  background: rgba(52, 211, 153, 0.16);
  color: #6ee7b7;
  border: 1px solid rgba(52, 211, 153, 0.3);
}
.model-badge.pro {
  background: rgba(96, 165, 250, 0.16);
  color: #93c5fd;
  border: 1px solid rgba(96, 165, 250, 0.3);
}
.model-badge.glm {
  background: rgba(192, 132, 252, 0.16);
  color: #d8b4fe;
  border: 1px solid rgba(192, 132, 252, 0.3);
}
.bubble {
  padding: 13px 17px;
  border-radius: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  white-space: pre-wrap;
  word-break: break-word;
  box-shadow: var(--shadow-soft);
}
.msg.user .bubble {
  background: var(--gradient-primary);
  border-color: rgba(99, 102, 241, 0.5);
  color: #fff;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.25);
}
.msg.coach .bubble {
  background: rgba(251, 191, 36, 0.1);
  border-color: rgba(251, 191, 36, 0.35);
  box-shadow: 0 4px 16px rgba(251, 191, 36, 0.1);
}
.msg-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 7px;
  padding: 0 4px;
}
.tts-btn {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: var(--radius-pill);
  background: var(--bg-hover);
  border: 1px solid var(--border);
  color: var(--text-soft);
  cursor: pointer;
  transition: all 0.2s;
}
.tts-btn:hover:not(:disabled) {
  color: var(--primary-soft);
  border-color: rgba(99, 102, 241, 0.4);
  background: rgba(99, 102, 241, 0.1);
}
.tts-btn:disabled {
  opacity: 0.6;
  cursor: default;
}
.tts-err {
  font-size: 11px;
  color: var(--danger);
}

/* markdown 内容 */
.md :deep(p) {
  margin: 0 0 8px;
}
.md :deep(p:last-child) {
  margin-bottom: 0;
}
.md :deep(pre) {
  background: rgba(0, 0, 0, 0.4);
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  overflow-x: auto;
  margin: 8px 0;
  font-size: 13px;
  border: 1px solid var(--border);
}
.md :deep(code) {
  font-family: 'Cascadia Code', Consolas, monospace;
}
.md :deep(:not(pre) > code) {
  background: var(--bg-hover);
  padding: 2px 6px;
  border-radius: var(--radius-xs);
  font-size: 13px;
}
.md :deep(ul),
.md :deep(ol) {
  padding-left: 20px;
  margin: 6px 0;
}
.md :deep(li) {
  margin: 4px 0;
}
.md :deep(h1),
.md :deep(h2),
.md :deep(h3) {
  margin: 12px 0 6px;
  font-size: 16px;
}
.md :deep(strong) {
  color: #fff;
}

@media (max-width: 768px) {
  .bubble-wrap {
    max-width: 84%;
  }
}
</style>
