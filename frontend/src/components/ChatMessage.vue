<script setup>
import { computed, ref, onBeforeUnmount } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import Icon from './Icon.vue'
import { modelBadge } from '../api'
import { speakText, stopSpeech } from '../utils/speech'
import { toast } from '../utils/toast'

const props = defineProps({
  role: { type: String, required: true }, // user | assistant
  content: { type: String, default: '' },
  coach: { type: Boolean, default: false },
  streaming: { type: Boolean, default: false },
  model: { type: String, default: '' },
  routeReason: { type: String, default: '' },
  retrieval: { type: Array, default: () => [] },
  fallback: { type: Boolean, default: false }
})

marked.setOptions({ breaks: true })

const html = computed(() => DOMPurify.sanitize(marked.parse(props.content || '')))
const isUser = computed(() => props.role === 'user')
const label = computed(() => (isUser.value ? '我' : props.coach ? 'AI 教练' : 'AI 面试官'))
const avatarIcon = computed(() => (isUser.value ? 'user' : props.coach ? 'graduation' : 'bot'))
const badge = computed(() => modelBadge(props.model))
const showCitations = ref(false)

const ttsPlaying = ref(false)
let speechController = null
const canAct = computed(() => !isUser.value && props.content && !props.streaming)

async function toggleTTS() {
  if (ttsPlaying.value) {
    speechController?.abort()
    stopSpeech()
    ttsPlaying.value = false
    return
  }
  try {
    stopSpeech()
    speechController = new AbortController()
    ttsPlaying.value = true
    await speakText(props.content, speechController.signal)
  } catch {
    toast.error('朗读暂不可用，请阅读文字内容')
  } finally {
    ttsPlaying.value = false
  }
}

async function copy() {
  try {
    await navigator.clipboard.writeText(props.content)
    toast.success('已复制到剪贴板')
  } catch {
    toast.error('复制失败，请手动选择文本')
  }
}

onBeforeUnmount(() => speechController?.abort())
</script>

<template>
  <div class="msg" :class="{ user: isUser, coach: coach && !isUser }">
    <div class="avatar" aria-hidden="true"><Icon :name="avatarIcon" :size="18" /></div>
    <div class="body">
      <div class="meta">
        <span class="who">{{ label }}</span>
        <span v-if="badge" class="model-badge" :title="'使用模型：' + model">{{ badge }}</span>
        <span v-if="fallback" class="tag tag-warning">基础引导</span>
      </div>

      <div v-if="isUser" class="bubble">{{ content }}</div>
      <div v-else class="bubble md">
        <div v-if="!content && streaming" class="thinking" aria-label="正在思考">
          <span></span><span></span><span></span>
        </div>
        <div v-else v-html="html"></div>
        <span v-if="streaming && content" class="caret" aria-hidden="true"></span>
      </div>

      <div v-if="canAct" class="actions">
        <button class="act" :class="{ on: ttsPlaying }" :aria-label="ttsPlaying ? '停止朗读' : '朗读'" @click="toggleTTS">
          <Icon :name="ttsPlaying ? 'stop' : 'volume'" :size="14" />{{ ttsPlaying ? '停止' : '朗读' }}
        </button>
        <button class="act" aria-label="复制" @click="copy"><Icon name="copy" :size="14" />复制</button>
        <button v-if="retrieval.length" class="act" :class="{ on: showCitations }" @click="showCitations = !showCitations">
          <Icon name="database" :size="14" />依据 {{ retrieval.length }}
        </button>
        <span v-if="routeReason" class="route" :title="routeReason"><Icon name="route" :size="12" />{{ routeReason }}</span>
      </div>

      <transition name="fade">
        <div v-if="showCitations && retrieval.length" class="citations">
          <div v-for="item in retrieval" :key="item.chunk_id || item.source" class="citation">
            <div class="row gap-2 wrap">
              <span class="tag tag-primary"><Icon name="fileText" :size="12" />{{ item.source || '资料' }}</span>
              <span v-if="item.document_type" class="tag">{{ item.document_type }}</span>
              <span v-if="item.page" class="text-xs text-dim">第 {{ item.page }} 页</span>
              <span class="text-xs text-dim ml-auto">相关度 {{ Math.round((item.score || 0) * 100) }}%</span>
            </div>
            <p v-if="item.excerpt" class="excerpt">{{ item.excerpt }}</p>
          </div>
        </div>
      </transition>
    </div>
  </div>
</template>

<style scoped>
.msg { display: flex; gap: 12px; max-width: 820px; margin: 0 auto 22px; animation: fadeInUp .3s var(--ease); }
.msg.user { flex-direction: row-reverse; }
.avatar {
  width: 34px; height: 34px; border-radius: 11px; flex-shrink: 0;
  display: grid; place-items: center;
  background: var(--gradient-primary); color: var(--text-on-primary);
  box-shadow: var(--shadow-glow);
}
.msg.user .avatar { background: var(--bg-hover); color: var(--text-soft); box-shadow: none; border: 1px solid var(--border); }
.msg.coach .avatar { background: var(--coach); box-shadow: none; }
.body { display: flex; flex-direction: column; min-width: 0; max-width: 82%; }
.msg.user .body { align-items: flex-end; }
.meta { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 12px; color: var(--text-dim); }
.who { font-weight: 600; color: var(--text-soft); }
.model-badge {
  font-size: 10px; font-family: var(--font-mono); padding: 1px 7px; border-radius: var(--radius-pill);
  background: var(--primary-bg); color: var(--primary-soft); border: 1px solid var(--primary-border);
}
.bubble {
  position: relative; padding: 12px 16px; border-radius: 4px var(--radius) var(--radius) var(--radius);
  background: var(--bg-card); border: 1px solid var(--border); box-shadow: var(--shadow-xs);
  word-break: break-word; line-height: 1.7;
}
.msg.user .bubble {
  white-space: pre-wrap; border-radius: var(--radius) 4px var(--radius) var(--radius);
  background: var(--gradient-primary); color: var(--text-on-primary); border-color: transparent;
}
.msg.coach .bubble { background: color-mix(in srgb, var(--coach) 9%, var(--bg-card)); border-color: color-mix(in srgb, var(--coach) 35%, transparent); }
.thinking { display: flex; gap: 5px; padding: 6px 2px; }
.thinking span { width: 7px; height: 7px; border-radius: 50%; background: var(--primary-soft); animation: pulse 1.2s infinite ease-in-out; }
.thinking span:nth-child(2) { animation-delay: .15s; }
.thinking span:nth-child(3) { animation-delay: .3s; }
.caret { display: inline-block; width: 7px; height: 15px; margin-left: 2px; vertical-align: -2px; background: var(--primary); animation: blink 1s steps(2) infinite; }
.actions { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; margin-top: 6px; opacity: .72; transition: opacity var(--dur); }
.msg:hover .actions { opacity: 1; }
.act {
  display: inline-flex; align-items: center; gap: 4px; padding: 4px 9px; font-size: 12px;
  border-radius: var(--radius-xs); color: var(--text-dim); background: transparent; border: none; cursor: pointer;
  transition: all var(--dur) var(--ease);
}
.act:hover, .act.on { color: var(--primary-soft); background: var(--primary-bg); }
.act:focus-visible { outline: 2px solid var(--primary); outline-offset: 1px; }
.route { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; color: var(--text-dim); max-width: 260px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.citations { margin-top: 8px; display: grid; gap: 8px; }
.citation { padding: 10px 12px; border-radius: var(--radius-sm); background: var(--bg-soft); border: 1px solid var(--border); }
.excerpt { margin: 6px 0 0; font-size: 12px; line-height: 1.6; color: var(--text-soft); }
@media (max-width: 768px) {
  .body { max-width: 88%; }
  .avatar { width: 30px; height: 30px; }
}
</style>
