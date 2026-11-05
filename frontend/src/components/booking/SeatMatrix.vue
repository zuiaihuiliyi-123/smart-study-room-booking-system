<script setup lang="ts">
import { computed, ref } from 'vue'

import SeatToolbar from '@/components/booking/SeatToolbar.vue'
import SeatZone from '@/components/booking/SeatZone.vue'
import type { MatrixCell, MatrixGroup } from '@/components/booking/types'

const props = defineProps<{
  groups: MatrixGroup[]
  selectedSeatId: number | null
  /** 我在当前时段已占的座位，图上单独标出 */
  mineIds?: readonly number[]
}>()

const emit = defineEmits<{ (e: 'select', cell: MatrixCell): void }>()

/* ---------------------------------------------------------------- 缩放 */
const ZOOM_KEY = 'ssr_seat_zoom'
const ZOOM_MIN = 0.6
const ZOOM_MAX = 2
const ZOOM_STEP = 0.2

function readZoom(): number {
  const saved = Number(globalThis.localStorage?.getItem(ZOOM_KEY))
  return Number.isFinite(saved) && saved >= ZOOM_MIN && saved <= ZOOM_MAX ? saved : 1
}

const zoom = ref(readZoom())
const zoomText = computed(() => `${Math.round(zoom.value * 100)}%`)

function applyZoom(next: number) {
  const clamped = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, Math.round(next * 10) / 10))
  zoom.value = clamped
  globalThis.localStorage?.setItem(ZOOM_KEY, String(clamped))
}

/** Ctrl / ⌘ + 滚轮缩放；普通滚轮仍然滚动平面图，不抢走用户的滚动习惯 */
function onWheel(event: WheelEvent) {
  if (!event.ctrlKey && !event.metaKey) return
  event.preventDefault()
  applyZoom(zoom.value + (event.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP))
}

const allCells = computed(() => props.groups.flatMap((group) => group.cells))

const counts = computed(() => {
  const result: Record<MatrixCell['state'], number> = {
    free: 0,
    taken: 0,
    unknown: 0,
    closed: 0,
    fix: 0,
    off: 0,
  }
  allCells.value.forEach((cell) => {
    result[cell.state] += 1
  })
  return result
})

/* ---------------------------------------------------------------- 桌位 */
/**
 * 一张桌子最多坐 6 人（3 列 × 2 排）；座位多的分区拆成几张一样长的桌子。
 *
 * 按「张数」均分而不是按 6 硬切，避免出现 10 个座位切成 6 + 4、最后一张桌
 * 只剩一个座位孤零零挂着的情况；每张桌的列数也随人数在 2～3 之间收放。
 */
const DESK_SIZE = 6

function splitDesks(cells: readonly MatrixCell[]): { rows: MatrixCell[][]; columns: number } {
  if (cells.length === 0) return { rows: [], columns: 3 }
  const deskCount = Math.ceil(cells.length / DESK_SIZE)
  const perDesk = Math.ceil(cells.length / deskCount)
  const rows: MatrixCell[][] = []
  for (let index = 0; index < cells.length; index += perDesk) {
    rows.push(cells.slice(index, index + perDesk))
  }
  const columns = Math.min(3, Math.max(2, Math.ceil(perDesk / 2)))
  return { rows, columns }
}

/** 分区按行列排：1～2 个分区一行摆满，3 个以上两列排开，避免又高又窄 */
const zoneColumns = computed(() => (props.groups.length <= 2 ? Math.max(1, props.groups.length) : 2))

const desks = computed(() =>
  props.groups.map((group) => {
    const layout = splitDesks(group.cells)
    return {
      key: group.key,
      title: group.title,
      cells: group.cells,
      desks: layout.rows,
      columns: layout.columns,
    }
  }),
)

/** 靠窗座位存在时，平面图顶部画一段「窗」，让人看出朝向 */
const hasWindowSeats = computed(() => allCells.value.some((cell) => cell.seat.near_window))
</script>

<template>
  <section class="seat-matrix" aria-label="座位图">
    <SeatToolbar
      :counts="counts"
      :zoom-text="zoomText"
      :can-zoom-out="zoom > ZOOM_MIN"
      :can-zoom-in="zoom < ZOOM_MAX"
      :can-reset="zoom !== 1"
      @zoom-out="applyZoom(zoom - ZOOM_STEP)"
      @zoom-in="applyZoom(zoom + ZOOM_STEP)"
      @zoom-reset="applyZoom(1)"
    />

    <div class="seat-floor" :style="{ '--seat-zoom': zoom }" @wheel="onWheel">
      <div class="room-plan">
        <span v-if="hasWindowSeats" class="room-plan__window" title="靠窗一侧">窗</span>

        <div class="seat-floor__zones" :style="{ '--zone-cols': zoneColumns }">
          <SeatZone
            v-for="zone in desks"
            :key="zone.key"
            :title="zone.title"
            :cells="zone.cells"
            :desks="zone.desks"
            :columns="zone.columns"
            :selected-seat-id="props.selectedSeatId"
            :mine-ids="props.mineIds"
            @select="emit('select', $event)"
          />
        </div>

        <span class="room-plan__door" aria-hidden="true">门</span>
        <span class="room-plan__note">平面示意</span>
      </div>

      <p v-if="!props.groups.length" class="seat-floor__empty">没有可显示的座位</p>
    </div>
  </section>
</template>

<style scoped>
/* 平面图：浅底 + 网格线，分区里按「桌子 + 椅子」摆放 */
.seat-floor {
  position: relative;
  min-height: 300px;
  max-height: 76vh;
  padding: 18px 16px 22px;
  overflow: auto;
  background-color: var(--ssr-bg);
  background-image:
    linear-gradient(to right, var(--ssr-line) 1px, transparent 1px),
    linear-gradient(to bottom, var(--ssr-line) 1px, transparent 1px);
  background-size: 28px 28px;
  border: 1px dashed var(--ssr-line-strong);
  border-radius: var(--ssr-radius);
  box-shadow: inset 0 0 42px -20px var(--ssr-line-strong);
  mask-image: radial-gradient(125% 120% at 50% 42%, #000 70%, transparent 100%);
}

/* 自习室本体：实线墙体 + 顶部窗带 + 底部门口的平面轮廓，
   外面的方格底当走廊，一眼能看出「这是一间多大的房、门在哪、窗在哪」 */
.room-plan {
  position: relative;
  padding: calc(22px * var(--seat-zoom, 1)) calc(18px * var(--seat-zoom, 1))
    calc(26px * var(--seat-zoom, 1));
  background:
    linear-gradient(180deg, var(--ssr-surface) 0%, var(--ssr-surface) 62%, var(--ssr-bg) 100%);
  border: calc(2px * var(--seat-zoom, 1)) solid var(--ssr-line-strong);
  border-radius: calc(10px * var(--seat-zoom, 1));
  box-shadow:
    0 12px 28px -20px var(--ssr-line-strong),
    inset 0 1px 0 var(--ssr-surface);
}

/* 窗：顶墙上一段双线，靠窗座位就在这一侧 */
.room-plan__window {
  position: absolute;
  top: calc(-3px * var(--seat-zoom, 1));
  left: 12%;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 76%;
  height: calc(13px * var(--seat-zoom, 1));
  font-size: calc(10px * var(--seat-zoom, 1));
  line-height: 1;
  color: var(--ssr-primary-ink);
  letter-spacing: 0.12em;
  background: linear-gradient(180deg, var(--ssr-primary-light), var(--ssr-surface));
  border: 1px solid var(--ssr-primary);
  border-width: 1px 0;
  border-radius: 2px;
}

/* 门：底墙上开一个缺口，写法上用与走廊同色的块盖住墙体，两侧留门框 */
.room-plan__note {
  position: absolute;
  right: calc(10px * var(--seat-zoom, 1));
  bottom: calc(4px * var(--seat-zoom, 1));
  font-size: calc(10px * var(--seat-zoom, 1));
  color: var(--ssr-muted-ink);
}

.room-plan__door {
  position: absolute;
  bottom: calc(-2px * var(--seat-zoom, 1));
  left: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  width: calc(72px * var(--seat-zoom, 1));
  height: calc(18px * var(--seat-zoom, 1));
  font-size: calc(11px * var(--seat-zoom, 1));
  color: var(--ssr-muted-ink);
  letter-spacing: 0.08em;
  background: var(--ssr-surface);
  border-right: calc(2px * var(--seat-zoom, 1)) solid var(--ssr-line-strong);
  border-bottom: calc(2px * var(--seat-zoom, 1)) solid var(--ssr-line-strong);
  border-left: calc(2px * var(--seat-zoom, 1)) solid var(--ssr-line-strong);
  border-radius: 0 0 calc(4px * var(--seat-zoom, 1)) calc(4px * var(--seat-zoom, 1));
  transform: translateX(-50%);
}

.seat-floor__zones {
  display: grid;
  grid-template-columns: repeat(var(--zone-cols, 2), minmax(0, 1fr));
  gap: calc(22px * var(--seat-zoom, 1)) calc(20px * var(--seat-zoom, 1));
  align-items: start;
  padding-top: 8px;
}
</style>
