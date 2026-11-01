<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import RingProgress from './RingProgress.vue'

const props = defineProps({
  match: { type: Object, default: null },
  diagnose: { type: Object, default: null },
})

const score = computed(() => props.match?.score ?? props.diagnose?.score ?? 0)
const levelIcon = { danger: 'xCircle', warning: 'alert', info: 'info' }
</script>

<template>
  <div v-if="match || diagnose" class="analysis card">
    <div class="top">
      <RingProgress :value="score" :size="84" :tone="score >= 80 ? 'success' : score >= 60 ? 'warning' : 'danger'">
        <b class="num">{{ score }}</b>
      </RingProgress>
      <div class="flex-1">
        <strong>{{ match ? '岗位匹配度' : '简历健康度' }}</strong>
        <p class="hint">
          {{ score >= 80 ? '匹配度很高，可以放心投递' : score >= 60 ? '基础不错，补齐缺失关键词会更有竞争力' : '与岗位差距较大，建议针对 JD 调整内容' }}
        </p>
      </div>
    </div>

    <div v-if="match?.matched?.length" class="block">
      <div class="field-label">已覆盖关键词</div>
      <div class="chips"><span v-for="w in match.matched" :key="w" class="tag tag-success">{{ w }}</span></div>
    </div>
    <div v-if="match?.missing?.length" class="block">
      <div class="field-label">缺失关键词</div>
      <div class="chips"><span v-for="w in match.missing" :key="w" class="tag tag-warning">{{ w }}</span></div>
    </div>

    <div v-if="diagnose?.issues?.length" class="block">
      <div class="field-label">诊断建议</div>
      <ul class="issues">
        <li v-for="(it, i) in diagnose.issues" :key="i" :class="it.level">
          <Icon :name="levelIcon[it.level] || 'info'" :size="14" />
          <span>{{ it.text }}</span>
        </li>
      </ul>
    </div>
  </div>
</template>

<style scoped>
.analysis { padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.top { display: flex; align-items: center; gap: 14px; }
.num { font-size: 22px; color: var(--text); }
.hint { margin: 4px 0 0; color: var(--text-soft); font-size: 13px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.issues { list-style: none; margin: 6px 0 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.issues li { display: flex; gap: 8px; align-items: flex-start; font-size: 13px; line-height: 1.6; color: var(--text-soft); }
.issues li svg { flex: none; margin-top: 3px; }
.issues .danger { color: var(--text); }
.issues .danger svg { color: #e5484d; }
.issues .warning svg { color: var(--warning); }
.issues .info svg { color: var(--primary); }
</style>
