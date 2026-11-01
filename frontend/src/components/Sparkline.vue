<script setup>
import { computed, useId } from 'vue'

const props = defineProps({
  values: { type: Array, default: () => [] },
  width: { type: Number, default: 120 },
  height: { type: Number, default: 40 },
  tone: { type: String, default: 'primary' },
})

const gid = `spark-${useId()}`
const pad = 3

const points = computed(() => {
  const v = props.values.map(Number).filter((n) => Number.isFinite(n))
  if (v.length < 2) return []
  const min = Math.min(...v)
  const max = Math.max(...v)
  const span = max - min || 1
  const w = props.width - pad * 2
  const h = props.height - pad * 2
  return v.map((n, i) => [pad + (i / (v.length - 1)) * w, pad + h - ((n - min) / span) * h])
})

const line = computed(() => points.value.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' '))
const area = computed(() => {
  if (!points.value.length) return ''
  const last = points.value[points.value.length - 1]
  const first = points.value[0]
  return `${line.value} L${last[0].toFixed(1)},${props.height} L${first[0].toFixed(1)},${props.height} Z`
})
const last = computed(() => points.value[points.value.length - 1])
</script>

<template>
  <svg
    v-if="points.length"
    class="spark"
    :class="`tone-${tone}`"
    :width="width"
    :height="height"
    :viewBox="`0 0 ${width} ${height}`"
    aria-hidden="true"
  >
    <defs>
      <linearGradient :id="gid" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="currentColor" stop-opacity=".28" />
        <stop offset="100%" stop-color="currentColor" stop-opacity="0" />
      </linearGradient>
    </defs>
    <path :d="area" :fill="`url(#${gid})`" />
    <path :d="line" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
    <circle v-if="last" :cx="last[0]" :cy="last[1]" r="3" fill="currentColor" />
  </svg>
</template>

<style scoped>
.spark { display: block; color: var(--primary-soft); }
.tone-success { color: var(--success); }
.tone-warning { color: var(--warning); }
.tone-info { color: var(--info); }
.tone-danger { color: var(--danger); }
</style>
