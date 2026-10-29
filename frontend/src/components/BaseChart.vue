<script setup lang="ts">
/**
 * ECharts 容器组件（FR-050 / FR-051：看板三张图共用）。
 *
 * 三个必须遵守的点（AGENTS.md §3、本轮任务「10 秒刷新的正确实现」）：
 * 1. **增量更新，不重建实例**：`setOption(option, { replaceMerge: ['series'] })`——
 *    只按 id 替换/新增 series，不 dispose 重建，动画与滚动位置都不会跳；
 *    `replaceMerge` 保证 series 数量变化（例如按自习室筛选后从 3 条变成 1 条）时不残留旧系列。
 * 2. **resize**：容器尺寸由栅格与侧栏折叠决定，不一定伴随 window resize，
 *    因此同时监听 `ResizeObserver` 与 `window.resize`。
 * 3. **dispose**：卸载时断开 observer、移除监听并 `chart.dispose()`，避免路由切换后实例泄漏。
 */
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

const props = withDefaults(
  defineProps<{
    option: EChartsOption
    height?: string
    /**
     * 图表的无障碍描述（NFR-007 / 本轮无障碍收口）。
     * canvas 里的图形对读屏软件不可读，因此容器用 role="img" + aria-label 把「这张图在讲什么、
     * 数据截至什么时候」用一句话说清楚；具体数值仍以页面上的卡片/表格为准。
     */
    label?: string
  }>(),
  { height: '300px', label: '图表' },
)

const container = ref<HTMLDivElement>()
let chart: echarts.ECharts | undefined
let observer: ResizeObserver | undefined
let frame = 0

function applyOption(): void {
  if (!chart || !props.option) return
  chart.setOption(props.option, { replaceMerge: ['series'], lazyUpdate: true })
}

function resize(): void {
  // 折叠/展开侧栏会连续触发多次尺寸变化，合并到一帧里执行
  if (frame !== 0) window.cancelAnimationFrame(frame)
  frame = window.requestAnimationFrame(() => {
    frame = 0
    chart?.resize()
  })
}

onMounted(() => {
  if (!container.value) return
  chart = echarts.init(container.value)
  applyOption()

  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => resize())
    observer.observe(container.value)
  }
  window.addEventListener('resize', resize)
})

watch(
  () => props.option,
  () => applyOption(),
  { deep: true },
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  if (frame !== 0) window.cancelAnimationFrame(frame)
  observer?.disconnect()
  observer = undefined
  chart?.dispose()
  chart = undefined
})
</script>

<template>
  <div
    ref="container"
    class="base-chart"
    role="img"
    :aria-label="label"
    :style="{ height }"
  />
</template>

<style scoped>
.base-chart {
  width: 100%;
}
</style>
