<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as echarts from 'echarts/core'
import { RadarChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

echarts.use([RadarChart, TooltipComponent, CanvasRenderer])

const props = defineProps({
  dimensions: { type: Array, default: () => [] }, // [{name, score}]
  compare: { type: Array, default: () => [] }, // 可选：对比基线 [{name, score}]
  height: { type: Number, default: 340 }
})

const chartEl = ref(null)
let chart = null
let observer = null
let resizeObserver = null

function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}

function render() {
  if (!chart || !props.dimensions.length) return
  const primary = cssVar('--primary', '#ff7ca2')
  const text = cssVar('--text-soft', '#cfcfd6')
  const border = cssVar('--border-strong', cssVar('--border', 'rgba(255,255,255,.2)'))
  const accent = cssVar('--text-dim', '#9a9aa3')
  const baseMap = Object.fromEntries(props.compare.map((d) => [d.name, d.score]))
  const series = [{
    value: props.dimensions.map((d) => d.score),
    name: '本次',
    areaStyle: { color: primary, opacity: 0.22 },
    lineStyle: { color: primary, width: 2 },
    itemStyle: { color: primary },
    symbolSize: 6
  }]
  if (props.compare.length) {
    series.unshift({
      value: props.dimensions.map((d) => baseMap[d.name] ?? 0),
      name: '首次',
      areaStyle: { color: accent, opacity: 0.06 },
      lineStyle: { color: accent, width: 1.5, type: 'dashed' },
      itemStyle: { color: accent },
      symbolSize: 4
    })
  }
  chart.setOption({
    tooltip: { trigger: 'item', confine: true },
    radar: {
      indicator: props.dimensions.map((d) => ({ name: d.name, max: 100 })),
      radius: '66%',
      splitNumber: 4,
      axisName: { color: text, fontSize: 12 },
      splitLine: { lineStyle: { color: border } },
      splitArea: { show: false },
      axisLine: { lineStyle: { color: border } }
    },
    series: [{ type: 'radar', data: series }]
  }, true)
}

onMounted(async () => {
  await nextTick()
  if (!chartEl.value) return
  chart = echarts.init(chartEl.value)
  render()
  resizeObserver = new ResizeObserver(() => chart?.resize())
  resizeObserver.observe(chartEl.value)
  // 主题切换时重绘以同步配色
  observer = new MutationObserver(render)
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] })
})

onBeforeUnmount(() => {
  observer?.disconnect()
  resizeObserver?.disconnect()
  chart?.dispose()
})

watch(() => [props.dimensions, props.compare], render, { deep: true })
</script>

<template>
  <div ref="chartEl" class="radar-chart" :style="{ height: height + 'px' }" role="img" :aria-label="'能力雷达图：' + dimensions.map((d) => `${d.name} ${d.score} 分`).join('，')"></div>
</template>

<style scoped>
.radar-chart { width: 100%; }
@media (max-width: 768px) {
  .radar-chart { height: 280px !important; }
}
</style>
