<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  keyword: { type: String, default: '' },
  compact: { type: Boolean, default: false },
})

const PLATFORMS = [
  { id: 'boss', name: 'BOSS直聘', url: (k) => `https://www.zhipin.com/web/geek/job?query=${k}` },
  { id: 'zhaopin', name: '智联招聘', url: (k) => `https://sou.zhaopin.com/?kw=${k}` },
  { id: 'liepin', name: '猎聘', url: (k) => `https://www.liepin.com/zhaopin/?key=${k}` },
  { id: '51job', name: '前程无忧', url: (k) => `https://search.51job.com/list/000000,000000,0000,00,9,99,${k},2,1.html` },
  { id: 'lagou', name: '拉勾', url: (k) => `https://www.lagou.com/wn/jobs?kd=${k}` },
]

const links = computed(() => {
  const k = encodeURIComponent(props.keyword.trim())
  return PLATFORMS.map((p) => ({ ...p, href: p.url(k) }))
})
</script>

<template>
  <div class="plat" :class="{ compact }">
    <a
      v-for="p in links"
      :key="p.id"
      class="plat-item"
      :href="p.href"
      target="_blank"
      rel="noopener noreferrer"
    >
      <span class="plat-name">{{ p.name }}</span>
      <Icon name="arrowUp" :size="14" class="plat-arrow" />
    </a>
  </div>
</template>

<style scoped>
.plat { display: flex; flex-wrap: wrap; gap: 10px; }
.plat-item {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 10px 14px; border-radius: var(--radius-sm);
  background: var(--bg-card); border: 1px solid var(--border);
  color: var(--text); font-size: 14px; font-weight: 500;
  transition: border-color var(--dur) var(--ease), background var(--dur) var(--ease), transform var(--dur) var(--ease);
}
.plat-item:hover { border-color: var(--primary-border); background: var(--bg-hover); transform: translateY(-1px); }
.plat-arrow { color: var(--primary-soft); transform: rotate(45deg); }
.compact .plat-item { padding: 6px 12px; font-size: 13px; border-radius: var(--radius-pill); }
</style>
