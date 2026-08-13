<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  dimensions: { type: Array, default: () => [] } // [{name, score, comment}]
})

const chartEl = ref(null)
let chart = null

function render() {
  if (!chart || !props.dimensions.length) return
  chart.setOption({
    radar: {
      indicator: props.dimensions.map((d) => ({ name: d.name, max: 100 })),
      shape: 'polygon',
      splitNumber: 4,
      axisName: { color: '#e2e8f0', fontSize: 13 },
      splitLine: { lineStyle: { color: '#334155' } },
      splitArea: { areaStyle: { color: ['rgba(79,70,229,0.05)', 'rgba(79,70,229,0.1)'] } },
      axisLine: { lineStyle: { color: '#334155' } }
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: props.dimensions.map((d) => d.score),
            name: '能力评估',
            areaStyle: { color: 'rgba(99,102,241,0.35)' },
            lineStyle: { color: '#6366f1', width: 2 },
            itemStyle: { color: '#818cf8' },
            label: { show: true, color: '#fff', fontSize: 12 }
          }
        ]
      }
    ]
  })
}

onMounted(async () => {
  await nextTick()
  if (chartEl.value) {
    chart = echarts.init(chartEl.value)
    render()
    window.addEventListener('resize', resize)
  }
})

function resize() {
  chart && chart.resize()
}

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart && chart.dispose()
})

watch(() => props.dimensions, render, { deep: true })
</script>

<template>
  <div ref="chartEl" class="radar-chart"></div>
</template>

<style scoped>
.radar-chart {
  width: 100%;
  height: 360px;
}
@media (max-width: 768px) {
  .radar-chart {
    height: 280px;
  }
}
</style>
