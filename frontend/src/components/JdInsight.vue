<script setup>
import Icon from './Icon.vue'

defineProps({ data: { type: Object, default: null } })
</script>

<template>
  <div v-if="data" class="jd-insight card">
    <div class="head">
      <Icon name="target" :size="16" />
      <strong>JD 解析</strong>
      <span v-if="data.role" class="tag tag-primary">{{ data.role }}</span>
      <span v-if="data.experience_years" class="tag tag-info">{{ data.experience_years }}</span>
      <span v-if="data.education" class="tag tag-info">{{ data.education }}</span>
    </div>

    <div v-if="data.keywords?.length" class="block">
      <div class="field-label">高频关键词</div>
      <div class="chips">
        <span
          v-for="k in data.keywords"
          :key="k.word"
          class="tag"
          :class="k.type === 'hard' ? 'tag-primary' : 'tag-success'"
        >{{ k.word }}<em v-if="k.count > 1"> ×{{ k.count }}</em></span>
      </div>
    </div>

    <div v-if="data.responsibilities?.length" class="block">
      <div class="field-label">岗位职责</div>
      <ul><li v-for="(t, i) in data.responsibilities" :key="i">{{ t }}</li></ul>
    </div>

    <div v-if="data.requirements?.length" class="block">
      <div class="field-label">任职要求</div>
      <ul><li v-for="(t, i) in data.requirements" :key="i">{{ t }}</li></ul>
    </div>

    <div v-if="data.tips?.length" class="block tips">
      <div class="field-label"><Icon name="bulb" :size="13" /> 投递建议</div>
      <ul><li v-for="(t, i) in data.tips" :key="i">{{ t }}</li></ul>
    </div>
  </div>
</template>

<style scoped>
.jd-insight { padding: 16px; display: flex; flex-direction: column; gap: 14px; }
.head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; color: var(--text); }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.chips em { font-style: normal; opacity: 0.7; margin-left: 2px; }
ul { margin: 6px 0 0; padding-left: 18px; color: var(--text-soft); font-size: 13px; line-height: 1.7; }
.tips { background: var(--primary-bg); border: 1px solid var(--primary-border); border-radius: var(--radius-sm); padding: 10px 12px; }
.tips .field-label { color: var(--primary); }
</style>
