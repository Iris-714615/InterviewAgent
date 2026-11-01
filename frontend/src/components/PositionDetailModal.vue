<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({
  position: { type: Object, default: null },
  category: { type: Object, default: null },
  actionText: { type: String, default: '选择该岗位' },
  actionIcon: { type: String, default: 'arrowRight' },
})
const emit = defineEmits(['close', 'select'])

function onKey(e) {
  if (e.key === 'Escape' && props.position) emit('close')
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div v-if="position" class="pdm-mask" @click.self="emit('close')">
      <div class="pdm" role="dialog" aria-modal="true" :aria-label="position.name">
        <button class="btn btn-ghost btn-icon pdm-close" aria-label="关闭" @click="emit('close')">
          <Icon name="x" :size="18" />
        </button>
        <div class="pdm-head">
          <span v-if="category" class="eyebrow">{{ category.name }}</span>
          <h3 class="pdm-title">
            {{ position.name }}
            <span v-if="position.hot" class="tag tag-warning">热门</span>
          </h3>
        </div>
        <div v-if="position.focus" class="pdm-block">
          <div class="pdm-label"><Icon name="target" :size="15" /> 面试考察重点</div>
          <p class="pdm-text">{{ position.focus }}</p>
        </div>
        <div v-if="position.skills?.length" class="pdm-block">
          <div class="pdm-label"><Icon name="layers" :size="15" /> 核心技能</div>
          <div class="pdm-skills">
            <span v-for="s in position.skills" :key="s" class="tag tag-primary">{{ s }}</span>
          </div>
        </div>
        <button class="btn btn-gradient btn-lg btn-block" @click="emit('select', position)">
          <Icon :name="actionIcon" :size="18" /> {{ actionText }}
        </button>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.pdm-mask {
  position: fixed; inset: 0; z-index: 200; display: grid; place-items: center;
  padding: 16px; background: var(--overlay); backdrop-filter: blur(6px);
}
.pdm {
  position: relative; width: min(520px, 100%); max-height: 86vh; overflow: auto;
  padding: 28px 24px 24px; border-radius: var(--radius-lg);
  background: var(--bg-elevated); border: 1px solid var(--border-strong);
  box-shadow: var(--shadow-card); animation: fadeInUp .25s var(--ease);
}
.pdm-close { position: absolute; top: 12px; right: 12px; }
.pdm-head { margin-bottom: 18px; padding-right: 36px; }
.pdm-title { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin: 6px 0 0; font-size: 22px; color: var(--text); }
.pdm-block { margin-bottom: 18px; }
.pdm-label { display: flex; align-items: center; gap: 6px; margin-bottom: 8px; font-size: 13px; font-weight: 600; color: var(--primary-soft); }
.pdm-text { margin: 0; line-height: 1.7; color: var(--text-soft); }
.pdm-skills { display: flex; flex-wrap: wrap; gap: 8px; }
@media (max-width: 640px) {
  .pdm-mask { align-items: end; padding: 0; }
  .pdm { width: 100%; border-radius: var(--radius-lg) var(--radius-lg) 0 0; }
}
</style>
