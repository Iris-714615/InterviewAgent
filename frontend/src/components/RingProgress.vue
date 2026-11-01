<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  size: { type: Number, default: 56 },
  stroke: { type: Number, default: 6 },
  tone: { type: String, default: 'primary' },
})

const r = computed(() => (props.size - props.stroke) / 2)
const c = computed(() => 2 * Math.PI * r.value)
const offset = computed(() => c.value * (1 - Math.min(100, Math.max(0, props.value)) / 100))
</script>

<template>
  <div class="ring" :class="`tone-${tone}`" :style="{ width: size + 'px', height: size + 'px' }">
    <svg :width="size" :height="size" :viewBox="`0 0 ${size} ${size}`" aria-hidden="true">
      <circle class="track" :cx="size / 2" :cy="size / 2" :r="r" fill="none" :stroke-width="stroke" />
      <circle
        class="bar"
        :cx="size / 2"
        :cy="size / 2"
        :r="r"
        fill="none"
        :stroke-width="stroke"
        stroke-linecap="round"
        :stroke-dasharray="c"
        :stroke-dashoffset="offset"
        :transform="`rotate(-90 ${size / 2} ${size / 2})`"
      />
    </svg>
    <div class="center"><slot /></div>
  </div>
</template>

<style scoped>
.ring { position: relative; display: inline-block; color: var(--primary-soft); }
.ring svg { display: block; }
.track { stroke: var(--bg-active); }
.bar { stroke: currentColor; transition: stroke-dashoffset .6s var(--ease); }
.center { position: absolute; inset: 0; display: grid; place-items: center; }
.tone-success { color: var(--success); }
.tone-warning { color: var(--warning); }
.tone-info { color: var(--info); }
.tone-danger { color: var(--danger); }
</style>
