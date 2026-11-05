<script setup lang="ts">
import { ArrowLeft, ArrowRight } from '@element-plus/icons-vue'
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import type { Room } from '@/types'

/**
 * 自习室切换条：横向滚动，装不下时两侧出现箭头。
 *
 * 自习室数量是不确定的（现在 3 间，以后可能几十间），所以这里不做固定列数，
 * 而是一条可滚动的带子——加自习室只是多一个按钮，不会把筛选条撑坏。
 */
const props = defineProps<{
  rooms: Room[]
  roomId: number | null
}>()

const emit = defineEmits<{
  (e: 'change', roomId: number): void
}>()

const strip = ref<HTMLElement | null>(null)
const overflowLeft = ref(false)
const overflowRight = ref(false)

function updateOverflow() {
  const el = strip.value
  if (!el) return
  overflowLeft.value = el.scrollLeft > 4
  overflowRight.value = el.scrollLeft + el.clientWidth < el.scrollWidth - 4
}

function scrollByPage(direction: number) {
  const el = strip.value
  if (!el) return
  el.scrollBy({ left: direction * Math.max(160, el.clientWidth * 0.6), behavior: 'smooth' })
}

function onWheel(event: WheelEvent) {
  const el = strip.value
  if (!el || el.scrollWidth <= el.clientWidth) return
  if (Math.abs(event.deltaY) <= Math.abs(event.deltaX)) return
  el.scrollLeft += event.deltaY
  event.preventDefault()
  updateOverflow()
}

/** 选中项自动滚进可视范围，避免新增自习室后当前项被挡住 */
function revealActive() {
  const el = strip.value
  if (!el) return
  const active = el.querySelector<HTMLElement>('.room-tab--on')
  if (!active) return
  const left = active.offsetLeft
  const right = left + active.offsetWidth
  if (left < el.scrollLeft) el.scrollLeft = left - 8
  else if (right > el.scrollLeft + el.clientWidth) el.scrollLeft = right - el.clientWidth + 8
  updateOverflow()
}

let observer: ResizeObserver | null = null

onMounted(() => {
  updateOverflow()
  if (typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(updateOverflow)
    if (strip.value) observer.observe(strip.value)
  }
})

onBeforeUnmount(() => {
  observer?.disconnect()
  observer = null
})

watch(
  () => [props.rooms.length, props.roomId],
  () => {
    void nextTick(revealActive)
  },
)
</script>

<template>
  <div class="room-strip">
    <button
      v-show="overflowLeft"
      class="room-strip__arrow"
      type="button"
      aria-label="向前翻自习室"
      @click="scrollByPage(-1)"
    >
      <el-icon><ArrowLeft /></el-icon>
    </button>

    <div ref="strip" class="room-tabs" role="group" aria-label="自习室" @scroll="updateOverflow" @wheel="onWheel">
      <button
        v-for="room in props.rooms"
        :key="room.id"
        type="button"
        class="room-tab"
        :class="{ 'room-tab--on': props.roomId === room.id }"
        @click="emit('change', room.id)"
      >
        {{ room.name }}
      </button>
    </div>

    <button
      v-show="overflowRight"
      class="room-strip__arrow"
      type="button"
      aria-label="向后翻自习室"
      @click="scrollByPage(1)"
    >
      <el-icon><ArrowRight /></el-icon>
    </button>
  </div>
</template>

<style scoped>
.room-strip {
  display: flex;
  flex: 1 1 220px;
  gap: 6px;
  align-items: center;
  min-width: 0;
}

.room-tabs {
  display: flex;
  flex: 1 1 auto;
  gap: 8px;
  align-items: center;
  overflow-x: auto;
  scrollbar-width: none;
}

.room-tabs::-webkit-scrollbar {
  height: 0;
}

.room-strip__arrow {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  color: var(--ssr-muted-ink);
  cursor: pointer;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: 999px;
}

.room-strip__arrow:hover {
  color: var(--ssr-primary-ink);
  border-color: var(--ssr-primary);
}

.room-tab {
  flex: 0 0 auto;
  padding: 4px 14px;
  font-size: var(--ssr-font-note);
  color: var(--ssr-ink);
  white-space: nowrap;
  cursor: pointer;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: 999px;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.room-tab:hover {
  border-color: var(--ssr-primary);
}

.room-tab--on {
  color: var(--ssr-on-primary);
  background: var(--ssr-primary);
  border-color: var(--ssr-primary);
}
</style>
