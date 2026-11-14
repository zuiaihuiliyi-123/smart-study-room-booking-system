<script setup lang="ts">
import { Check } from '@element-plus/icons-vue'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

import SeatMapList from '@/components/booking/SeatMapList.vue'
import SeatMapToolbar from '@/components/booking/SeatMapToolbar.vue'
import { SEAT_STATE_ICON, SEAT_STATE_NOTE } from '@/components/booking/seatState'
import type { MatrixCell, MatrixGroup } from '@/components/booking/types'
import type { Area } from '@/types'
import {
  seatAriaLabel,
  SEAT_STATE_TEXT,
  type SeatCellState,
} from '@/utils/bookingRules'
import {
  buildSeatMapLayout,
  type SeatMapChair,
  type SeatMapLayout,
  type SeatMapTable,
} from '@/utils/seatMapLayout'

/**
 * 预约地图：桌子 + 椅子家具模型。
 *
 * 桌子是空间对象，不响应选座；椅子是唯一可预约单元。
 * 座位数据仍来自 useSeatBooking 的 MatrixGroup，本组件只负责布局、缩放、平移与点击语义。
 */
const props = defineProps<{
  groups: MatrixGroup[]
  selectedSeatId: number | null
  mineIds?: readonly number[]
  areas?: readonly Area[]
}>()

const emit = defineEmits<{ (e: 'select', cell: MatrixCell): void }>()

const ZOOM_MIN = 0.5
const ZOOM_MAX = 2.5
const PAN_KEEP = 80

const layout = computed<SeatMapLayout>(() =>
  buildSeatMapLayout(props.groups, props.areas ?? []),
)
const mineSet = computed(() => new Set(props.mineIds ?? []))
const view = ref<'map' | 'list'>('map')
const shellRef = ref<HTMLElement | null>(null)
const stageRef = ref<HTMLElement | null>(null)
const transform = reactive({ x: 0, y: 0, z: 1 })
const hoveredTableId = ref<string | null>(null)
const dragging = ref(false)
const autoFit = ref(true)
const suppressClick = ref(false)
const pointers = new Map<number, { x: number; y: number }>()
let pan: { startX: number; startY: number; originX: number; originY: number; moved: boolean } | null = null
let pinch: { distance: number; z: number; x: number; y: number; worldX: number; worldY: number } | null = null
let resizeObserver: ResizeObserver | null = null

const stageStyle = computed<Record<string, string>>(() => {
  const z = transform.z
  /*
   * 位置取整：平移量带小数（例如 230.375px）时，画布里的文字和 1px 描边
   * 会落在半像素上，整体看起来发糊；取整后贴回物理像素格，字才清晰。
   */
  const x = Math.round(transform.x)
  const y = Math.round(transform.y)
  const chairFont = Math.min(20, Math.max(9, 11 / z))
  const tableFont = Math.min(18, Math.max(7, 10 / z))
  return {
    width: `${layout.value.width}px`,
    height: `${layout.value.height}px`,
    transform: `translate(${x}px, ${y}px) scale(${z})`,
    '--chair-font': `${chairFont.toFixed(2)}px`,
    '--table-font': `${tableFont.toFixed(2)}px`,
  }
})

const lod = computed(() => (transform.z < 0.62 ? 'far' : transform.z < 1.12 ? 'mid' : 'near'))
const zoomText = computed(() => `${Math.round(transform.z * 100)}%`)
const canZoomOut = computed(() => transform.z > ZOOM_MIN + 0.001)
const canZoomIn = computed(() => transform.z < ZOOM_MAX - 0.001)

const counts = computed<Record<SeatCellState, number>>(() => {
  const result: Record<SeatCellState, number> = {
    free: 0,
    taken: 0,
    unknown: 0,
    closed: 0,
    fix: 0,
    off: 0,
  }
  layout.value.chairs.forEach((chair) => {
    if (chair.cell.matched === false) return
    result[chair.cell.state] += 1
  })
  return result
})
/** 不符合当前筛选的椅子：保留原位置淡显，不计入状态图例。 */
const filteredCount = computed(
  () => layout.value.chairs.filter((chair) => chair.cell.matched === false).length,
)
const mineCount = computed(() =>
  layout.value.chairs.filter(
    (chair) => chair.cell.matched !== false && mineSet.value.has(chair.cell.seat.id),
  ).length,
)
const selectedTableId = computed(() => {
  if (props.selectedSeatId === null) return null
  return layout.value.chairs.find((chair) => chair.cell.seat.id === props.selectedSeatId)?.tableId ?? null
})

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

function chairStyle(chair: SeatMapChair): Record<string, string> {
  return {
    left: `${chair.x}px`,
    top: `${chair.y}px`,
    width: `${chair.w}px`,
    height: `${chair.h}px`,
  }
}

function tableStyle(table: SeatMapTable): Record<string, string> {
  return {
    left: `${table.x}px`,
    top: `${table.y}px`,
    width: `${table.w}px`,
    height: `${table.h}px`,
  }
}

function chairClass(chair: SeatMapChair): Record<string, boolean> {
  const mine = mineSet.value.has(chair.cell.seat.id)
  return {
    'map-chair--selected': props.selectedSeatId === chair.cell.seat.id,
    'map-chair--mine': mine,
    'map-chair--filtered': chair.cell.matched === false,
    'map-chair--table-hover': hoveredTableId.value === chair.tableId,
    [`map-chair--${chair.cell.state}`]: true,
    [`map-chair--${chair.orientation}`]: true,
  }
}

function chairFiltered(chair: SeatMapChair): boolean {
  return chair.cell.matched === false
}

function chairLabel(chair: SeatMapChair): string {
  const base = seatAriaLabel(chair.cell.seat, chair.cell.state)
  if (chairFiltered(chair)) return `${base}，不符合当前筛选，不可预约`
  return mineSet.value.has(chair.cell.seat.id) ? `${base}，这是你在这个时段的预约` : base
}

function chairTitle(chair: SeatMapChair): string {
  if (chairFiltered(chair)) return `${chair.cell.seat.seat_no} · 不符合当前筛选`
  const state = mineSet.value.has(chair.key) ? '我的预约' : SEAT_STATE_TEXT[chair.cell.state]
  return `${chair.cell.seat.seat_no} · ${state}`
}

/*
 * 悬停信息卡：浏览器自带的 title 提示要等一秒左右、样式也改不了。
 * 这里自己画一张小卡片，位置取椅子在画布里的屏幕坐标（画布本身不参与缩放），
 * 所以无论缩放到多少，卡片都贴着椅子且字号恒定。
 */
interface ChairHoverCard {
  seatNo: string
  stateText: string
  mine: boolean
  meta: string
  x: number
  y: number
  below: boolean
}

const hoverCard = ref<ChairHoverCard | null>(null)

function onChairEnter(event: PointerEvent, chair: SeatMapChair): void {
  const shell = shellRef.value
  if (!shell || dragging.value) return
  const target = event.currentTarget as HTMLElement | null
  if (!target) return
  const box = target.getBoundingClientRect()
  const frame = shell.getBoundingClientRect()
  const mine = mineSet.value.has(chair.key)
  const meta = [
    chair.cell.seat.seat_type,
    chair.cell.seat.has_power ? '有插座' : '',
    chair.cell.seat.near_window ? '靠窗' : '',
  ].filter(Boolean)
  const y = box.top - frame.top
  hoverCard.value = {
    seatNo: chair.cell.seat.seat_no,
    stateText: chairFiltered(chair) ? '不符合当前筛选' : mine ? '我的预约' : SEAT_STATE_TEXT[chair.cell.state],
    mine,
    meta: meta.join(' · '),
    x: box.left - frame.left + box.width / 2,
    y,
    below: y < 64,
  }
}

function clampViewport(): void {
  const shell = shellRef.value
  if (!shell) return
  const width = layout.value.width * transform.z
  const height = layout.value.height * transform.z
  const rw = shell.clientWidth
  const rh = shell.clientHeight
  if (width <= rw) transform.x = (rw - width) / 2
  else transform.x = clamp(transform.x, rw - width - PAN_KEEP, PAN_KEEP)
  if (height <= rh) transform.y = (rh - height) / 2
  else transform.y = clamp(transform.y, rh - height - PAN_KEEP, PAN_KEEP)
}

function fitMap(): void {
  const shell = shellRef.value
  if (!shell) return
  const padding = shell.clientWidth < 620 ? 10 : 26
  const z = clamp(
    Math.min(
      (shell.clientWidth - padding * 2) / layout.value.width,
      (shell.clientHeight - padding * 2) / layout.value.height,
    ),
    ZOOM_MIN,
    ZOOM_MAX,
  )
  transform.z = z
  transform.x = (shell.clientWidth - layout.value.width * z) / 2
  transform.y = (shell.clientHeight - layout.value.height * z) / 2
  autoFit.value = true
  clampViewport()
}

function resetMap(): void {
  const shell = shellRef.value
  if (!shell) return
  transform.z = 1
  transform.x = (shell.clientWidth - layout.value.width) / 2
  transform.y = (shell.clientHeight - layout.value.height) / 2
  autoFit.value = false
  clampViewport()
}

function zoomAt(clientX: number, clientY: number, nextZ: number): void {
  const shell = shellRef.value
  if (!shell) return
  const rect = shell.getBoundingClientRect()
  const localX = clientX - rect.left
  const localY = clientY - rect.top
  const worldX = (localX - transform.x) / transform.z
  const worldY = (localY - transform.y) / transform.z
  transform.z = clamp(nextZ, ZOOM_MIN, ZOOM_MAX)
  transform.x = localX - worldX * transform.z
  transform.y = localY - worldY * transform.z
  autoFit.value = false
  clampViewport()
}

function zoomBy(factor: number): void {
  const shell = shellRef.value
  if (!shell) return
  zoomAt(shell.clientWidth / 2, shell.clientHeight / 2, transform.z * factor)
}

/* ------------------------------ 缩略导航 ------------------------------ */

const MINI_W = 132
const MINI_H = 96

/** 把整张平面图塞进角落的缩放比 */
const miniScale = computed(() =>
  Math.min(MINI_W / layout.value.width, MINI_H / layout.value.height),
)

const miniSize = computed(() => ({
  w: Math.round(layout.value.width * miniScale.value),
  h: Math.round(layout.value.height * miniScale.value),
}))

/** 当前视野（换算回图纸坐标），裁剪到图纸范围内，避免视野框画到外框上 */
const miniViewport = computed(() => {
  const z = transform.z || 1
  const width = layout.value.width
  const height = layout.value.height
  const x = clamp(-transform.x / z, 0, width)
  const y = clamp(-transform.y / z, 0, height)
  return {
    x,
    y,
    w: Math.max(1, Math.min(shellSize.w / z, width - x)),
    h: Math.max(1, Math.min(shellSize.h / z, height - y)),
  }
})

/** 放大到看不见整张图时才给缩略导航，适配状态不占地方 */
const showMini = computed(() => {
  const view = miniViewport.value
  return view.w < layout.value.width - 6 || view.h < layout.value.height - 6
})

const miniDragging = ref(false)

/** 缩略图上的点 → 图纸坐标 */
function miniWorldFrom(event: PointerEvent): { x: number; y: number } {
  const el = event.currentTarget as HTMLElement
  const rect = el.getBoundingClientRect()
  const scale = miniScale.value || 1
  return { x: (event.clientX - rect.left) / scale, y: (event.clientY - rect.top) / scale }
}

/** 把缩略图上点到的位置移到视野中心 */
function miniCenterOn(event: PointerEvent): void {
  const world = miniWorldFrom(event)
  transform.x = shellSize.w / 2 - world.x * transform.z
  transform.y = shellSize.h / 2 - world.y * transform.z
  autoFit.value = false
  clampViewport()
}

function onMiniDown(event: PointerEvent): void {
  if (event.pointerType === 'mouse' && event.button !== 0) return
  event.preventDefault()
  miniDragging.value = true
  ;(event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId)
  miniCenterOn(event)
}

function onMiniMove(event: PointerEvent): void {
  if (!miniDragging.value) return
  miniCenterOn(event)
}

function onMiniUp(event: PointerEvent): void {
  if (!miniDragging.value) return
  miniDragging.value = false
  ;(event.currentTarget as HTMLElement).releasePointerCapture?.(event.pointerId)
}

/**
 * 滚轮语义：Ctrl / ⌘ + 滚轮缩放，普通滚轮放行给页面滚动。
 *
 * 之前无差别 `preventDefault()` + 缩放，鼠标停在图上滚页面时页面不动、地图反而缩小，
 * 用户会认为「滚轮坏了」。触控板的双指缩放由 pointer 事件单独处理，不受这里影响。
 */
function onWheel(event: WheelEvent): void {
  if (!event.ctrlKey && !event.metaKey) return
  event.preventDefault()
  zoomAt(event.clientX, event.clientY, transform.z * Math.exp(-event.deltaY * 0.0016))
}

function onPointerDown(event: PointerEvent): void {
  if (event.pointerType === 'mouse' && event.button !== 0) return
  const shell = shellRef.value
  if (!shell) return
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY })
  if (pointers.size === 2) {
    const [a, b] = [...pointers.values()]
    const rect = shell.getBoundingClientRect()
    const midX = (a.x + b.x) / 2 - rect.left
    const midY = (a.y + b.y) / 2 - rect.top
    pinch = {
      distance: Math.max(1, Math.hypot(a.x - b.x, a.y - b.y)),
      z: transform.z,
      x: transform.x,
      y: transform.y,
      worldX: (midX - transform.x) / transform.z,
      worldY: (midY - transform.y) / transform.z,
    }
    pan = null
    return
  }
  pan = {
    startX: event.clientX,
    startY: event.clientY,
    originX: transform.x,
    originY: transform.y,
    moved: false,
  }
  dragging.value = true
  hoverCard.value = null
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
  window.addEventListener('pointercancel', onPointerUp)
}

function onPointerMove(event: PointerEvent): void {
  if (!pointers.has(event.pointerId)) return
  pointers.set(event.pointerId, { x: event.clientX, y: event.clientY })
  const shell = shellRef.value
  if (!shell) return

  if (pointers.size >= 2 && pinch) {
    const [a, b] = [...pointers.values()]
    const rect = shell.getBoundingClientRect()
    const midX = (a.x + b.x) / 2 - rect.left
    const midY = (a.y + b.y) / 2 - rect.top
    const distance = Math.max(1, Math.hypot(a.x - b.x, a.y - b.y))
    transform.z = clamp(pinch.z * (distance / pinch.distance), ZOOM_MIN, ZOOM_MAX)
    transform.x = midX - pinch.worldX * transform.z
    transform.y = midY - pinch.worldY * transform.z
    autoFit.value = false
    suppressClick.value = true
    clampViewport()
    return
  }

  if (!pan) return
  const dx = event.clientX - pan.startX
  const dy = event.clientY - pan.startY
  if (!pan.moved && Math.hypot(dx, dy) > 4) pan.moved = true
  if (!pan.moved) return
  transform.x = pan.originX + dx
  transform.y = pan.originY + dy
  autoFit.value = false
  suppressClick.value = true
  clampViewport()
}

function onPointerUp(event: PointerEvent): void {
  const wasPinching = pinch !== null
  pointers.delete(event.pointerId)
  if (pointers.size < 2) pinch = null
  if (pan?.moved || wasPinching) {
    suppressClick.value = true
    window.setTimeout(() => {
      suppressClick.value = false
    }, 0)
  }
  pan = null
  dragging.value = false
  if (pointers.size === 0) {
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
    window.removeEventListener('pointercancel', onPointerUp)
  }
}

function onChairClick(cell: MatrixCell): void {
  if (suppressClick.value || cell.matched === false) return
  emit('select', cell)
}

function onShellKeydown(event: KeyboardEvent): void {
  if (event.target !== shellRef.value) return
  const step = event.shiftKey ? 88 : 34
  if (event.key === 'ArrowLeft') { event.preventDefault(); transform.x += step; clampViewport() }
  else if (event.key === 'ArrowRight') { event.preventDefault(); transform.x -= step; clampViewport() }
  else if (event.key === 'ArrowUp') { event.preventDefault(); transform.y += step; clampViewport() }
  else if (event.key === 'ArrowDown') { event.preventDefault(); transform.y -= step; clampViewport() }
  else if (event.key === '+' || event.key === '=') { event.preventDefault(); zoomBy(1.2) }
  else if (event.key === '-') { event.preventDefault(); zoomBy(1 / 1.2) }
  else if (event.key === '0') { event.preventDefault(); resetMap() }
  else if (event.key.toLowerCase() === 'f') { event.preventDefault(); fitMap() }
}

function focusAdjacentChair(current: SeatMapChair, key: string): void {
  const direction = {
    ArrowRight: [1, 0],
    ArrowLeft: [-1, 0],
    ArrowDown: [0, 1],
    ArrowUp: [0, -1],
  }[key]
  if (!direction) return
  const cx = current.x + current.w / 2
  const cy = current.y + current.h / 2
  let best: SeatMapChair | null = null
  let score = Infinity
  for (const chair of layout.value.chairs) {
    if (chair.key === current.key || chair.cell.matched === false) continue
    const dx = chair.x + chair.w / 2 - cx
    const dy = chair.y + chair.h / 2 - cy
    const forward = dx * direction[0] + dy * direction[1]
    if (forward <= 3) continue
    const perp = Math.abs(dx * direction[1] - dy * direction[0])
    const candidate = forward + perp * 0.55
    if (candidate < score) {
      score = candidate
      best = chair
    }
  }
  if (best) {
    const target = stageRef.value?.querySelector<HTMLButtonElement>(`[data-seat-id="${best.key}"]`)
    target?.focus({ preventScroll: true })
  }
}

function onChairKeydown(event: KeyboardEvent, chair: SeatMapChair): void {
  if (event.key.startsWith('Arrow')) {
    event.preventDefault()
    focusAdjacentChair(chair, event.key)
  }
}

function toggleView(next: 'map' | 'list'): void {
  view.value = next
  if (next === 'map') {
    void nextTick(() => {
      if (autoFit.value) fitMap()
      else {
        clampViewport()
      }
    })
  }
}

function rebuildAfterLayoutChange(): void {
  void nextTick(() => {
    if (autoFit.value) fitMap()
    else {
      clampViewport()
    }
  })
}

/** 画布可视区尺寸：缩略导航要用它换算「当前看到的是整图的哪一块」 */
const shellSize = reactive({ w: 0, h: 0 })

function measureShell(): void {
  const shell = shellRef.value
  if (!shell) return
  shellSize.w = shell.clientWidth
  shellSize.h = shell.clientHeight
}

function observeShell(): void {
  resizeObserver?.disconnect()
  const shell = shellRef.value
  if (!shell) return
  measureShell()
  resizeObserver = new ResizeObserver(() => {
    measureShell()
    if (autoFit.value) fitMap()
    else {
      clampViewport()
    }
  })
  resizeObserver.observe(shell)
}

watch(layout, rebuildAfterLayoutChange)
watch(shellRef, observeShell, { flush: 'post' })

onMounted(() => {
  observeShell()
  void nextTick(() => {
    /* 极窄容器（例如手机窄栏）地图缩到 50% 仍会裁切，先给可点击的列表兜底；
       工具条仍可切回地图，地图支持拖拽 / 双指缩放。 */
    if ((shellRef.value?.clientWidth ?? 0) < 520) {
      view.value = 'list'
      return
    }
    fitMap()
  })
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  window.removeEventListener('pointercancel', onPointerUp)
})
</script>

<template>
  <section class="seat-map" aria-label="自习室座位地图">
    <SeatMapToolbar
      :counts="counts"
      :filtered-count="filteredCount"
      :mine-count="mineCount"
      :zoom-text="zoomText"
      :can-zoom-out="canZoomOut"
      :can-zoom-in="canZoomIn"
      :view="view"
      @zoom-out="zoomBy(1 / 1.2)"
      @zoom-in="zoomBy(1.2)"
      @fit="fitMap"
      @reset="resetMap"
      @toggle-view="toggleView"
    />

    <div
      v-if="view === 'map'"
      ref="shellRef"
      class="seat-map__shell"
      :class="{ 'is-dragging': dragging }"
      tabindex="0"
      role="region"
      aria-label="自习室平面图。拖拽平移，Ctrl 加滚轮或双指缩放；用 Tab 浏览椅子，回车选择。"
      @pointerdown="onPointerDown"
      @keydown="onShellKeydown"
      @wheel="onWheel"
    >
      <div ref="stageRef" class="seat-map__stage" :style="stageStyle" :data-lod="lod">
        <div class="seat-map__floor" :style="{ width: `${layout.width}px`, height: `${layout.height}px` }">
          <svg class="seat-map__arch" :viewBox="`0 0 ${layout.width} ${layout.height}`" aria-hidden="true">
            <rect
              x="20"
              y="20"
              :width="layout.width - 40"
              :height="layout.height - 40"
              rx="26"
              class="arch-wall"
            />
            <template v-if="layout.hasWindow">
              <path :d="`M62 20 H ${layout.width - 240}`" class="arch-window" />
              <path :d="`M62 26 H ${layout.width - 240}`" class="arch-window arch-window--faint" />
              <path
                v-for="index in 12"
                :key="index"
                :d="`M${62 + ((layout.width - 302) / 11) * (index - 1)} 20 V26`"
                class="arch-window-tick"
              />
              <text x="86" y="13" class="arch-label">北窗 · NATURAL LIGHT</text>
            </template>
            <template v-if="layout.zones.length > 1">
              <path
                v-for="zone in layout.zones.filter((item, index) => index > 0)"
                :key="`${zone.id}-divider`"
                :d="`M20 ${zone.y - 7} H ${layout.width - 20}`"
                class="arch-divider"
              />
            </template>
            <path :d="`M${layout.width - 104} ${layout.height - 40} v-54`" class="arch-door" />
            <path
              :d="`M${layout.width - 104} ${layout.height - 94} a54 54 0 0 1 54 54`"
              class="arch-door-arc"
            />
            <text :x="layout.width - 77" :y="layout.height - 16" class="arch-label" text-anchor="middle">主入口 · ENTRANCE</text>
            <path :d="`M42 ${layout.height - 128} H ${layout.width - 42}`" class="arch-aisle" />
            <text :x="layout.width / 2" :y="layout.height - 134" class="arch-label" text-anchor="middle">主通道 / AISLE</text>
            <path :d="`M42 ${layout.height - 25} H 92 M42 ${layout.height - 29} V ${layout.height - 21} M92 ${layout.height - 29} V ${layout.height - 21}`" class="arch-scale" />
            <text x="67" :y="layout.height - 14" class="arch-label" text-anchor="middle">1m</text>
          </svg>

          <div
            v-for="zone in layout.zones"
            :key="zone.id"
            class="map-zone"
            :class="`map-zone--${zone.kind}`"
            :style="{ left: `${zone.x}px`, top: `${zone.y}px`, width: `${zone.w}px`, height: `${zone.h}px` }"
          >
            <span class="map-zone__label">
              <strong>{{ zone.label }}</strong>
              <em>{{ zone.en }}</em>
            </span>
          </div>

          <div
            v-for="table in layout.tables"
            :key="table.id"
            class="map-table"
            :class="[
              `map-table--${table.shape}`,
              `map-table--${table.kind}`,
              {
                'is-hovered': hoveredTableId === table.id,
                'is-selected': selectedTableId === table.id,
              },
            ]"
            :style="tableStyle(table)"
            aria-hidden="true"
            @pointerenter="hoveredTableId = table.id"
            @pointerleave="hoveredTableId = null"
          >
            <span class="map-table__label">
              <strong>{{ table.label }}</strong>
              <span v-for="tag in table.tags" :key="tag" class="map-table__tag">{{ tag }}</span>
            </span>
            <span class="map-table__meta">{{ table.meta }}</span>
          </div>

          <button
            v-for="chair in layout.chairs"
            :key="chair.key"
            type="button"
            class="map-chair"
            :class="chairClass(chair)"
            :style="chairStyle(chair)"
            :data-seat-id="chair.key"
            :disabled="chairFiltered(chair)"
            :aria-label="chairLabel(chair)"
            :aria-pressed="props.selectedSeatId === chair.cell.seat.id"
            :title="chairTitle(chair)"
            @pointerenter="onChairEnter($event, chair)"
            @pointerleave="hoverCard = null"
            @click="onChairClick(chair.cell)"
            @keydown="onChairKeydown($event, chair)"
          >
            <span class="map-chair__back" aria-hidden="true" />
            <span class="map-chair__pad">
              <span class="map-chair__no">
                <span class="map-chair__no-full">{{ chair.cell.seat.seat_no }}</span>
                <span class="map-chair__no-short">{{ chair.cell.seat.seat_no.split('-').pop() }}</span>
              </span>
              <span v-if="!chairFiltered(chair) && mineSet.has(chair.key)" class="map-chair__mine">我的</span>
              <span
                v-if="!chairFiltered(chair) && !mineSet.has(chair.key) && chair.cell.state !== 'free'"
                class="map-chair__state"
                :title="SEAT_STATE_NOTE[chair.cell.state]"
                aria-hidden="true"
              >
                <el-icon><component :is="SEAT_STATE_ICON[chair.cell.state]" /></el-icon>
              </span>
              <span
                v-else-if="!chairFiltered(chair) && mineSet.has(chair.key)"
                class="map-chair__state"
                aria-hidden="true"
              >
                <el-icon><Check /></el-icon>
              </span>
            </span>
          </button>

          <div class="map-front-desk" :style="{ left: `${layout.width / 2 - 74}px`, top: `${layout.height - 104}px` }">
            <strong>前台</strong>
            <span>SERVICE</span>
          </div>
        </div>
      </div>

      <div
        v-if="hoverCard"
        class="seat-hover"
        :class="{ 'seat-hover--below': hoverCard.below }"
        :style="{ left: `${hoverCard.x}px`, top: `${hoverCard.y}px` }"
        role="presentation"
      >
        <span class="seat-hover__no">{{ hoverCard.seatNo }}</span>
        <span class="seat-hover__state" :class="{ 'seat-hover__state--mine': hoverCard.mine }">
          {{ hoverCard.stateText }}
        </span>
        <span class="seat-hover__meta">{{ hoverCard.meta }}</span>
      </div>

      <p class="seat-map__hint">
        <span>拖拽平移</span>
        <span>Ctrl + 滚轮 / 双指缩放</span>
        <span>点击椅子查看</span>
        <span v-if="filteredCount > 0">淡色椅子不符合当前筛选</span>
      </p>

      <!-- 缩略导航：放大到看不全时，用它拖到想去的位置 -->
      <div
        v-if="showMini"
        class="seat-mini"
        :style="{ width: `${miniSize.w}px`, height: `${miniSize.h}px` }"
        role="presentation"
        aria-hidden="true"
        @pointerdown="onMiniDown"
        @pointermove="onMiniMove"
        @pointerup="onMiniUp"
        @pointercancel="onMiniUp"
      >
        <svg class="seat-mini__svg" :viewBox="`0 0 ${layout.width} ${layout.height}`">
          <rect
            v-for="zone in layout.zones"
            :key="zone.id"
            class="seat-mini__zone"
            :x="zone.x"
            :y="zone.y"
            :width="zone.w"
            :height="zone.h"
          />
          <rect
            v-for="table in layout.tables"
            :key="table.id"
            class="seat-mini__table"
            :x="table.x"
            :y="table.y"
            :width="table.w"
            :height="table.h"
            :rx="table.shape === 'round' ? Math.min(table.w, table.h) / 2 : 4"
          />
          <rect
            class="seat-mini__view"
            :x="miniViewport.x"
            :y="miniViewport.y"
            :width="miniViewport.w"
            :height="miniViewport.h"
          />
        </svg>
      </div>
    </div>

    <SeatMapList
      v-else
      :layout="layout"
      :selected-seat-id="props.selectedSeatId"
      :mine-ids="props.mineIds"
      @select="emit('select', $event)"
    />
  </section>
</template>

<style scoped>
.seat-map {
  min-width: 0;
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
  box-shadow: var(--ssr-shadow-sm);
}

.seat-map__shell {
  position: relative;
  height: clamp(470px, 60vh, 700px);
  overflow: hidden;
  cursor: grab;
  touch-action: none;
  background:
    linear-gradient(90deg, color-mix(in srgb, var(--ssr-line) 34%, transparent) 1px, transparent 1px) 0 0 / 24px 24px,
    linear-gradient(color-mix(in srgb, var(--ssr-line) 34%, transparent) 1px, transparent 1px) 0 0 / 24px 24px,
    var(--ssr-bg);
}

.seat-map__shell:focus-visible {
  outline: 2px solid var(--ssr-primary);
  outline-offset: -3px;
}

.seat-map__shell.is-dragging {
  cursor: grabbing;
}

.seat-map__stage {
  position: absolute;
  top: 0;
  left: 0;
  /*
   * 不要 will-change：提前提升为合成层会让浏览器按 1 倍光栅化后再缩放，
   * 缩放不是整数时整张图的文字都会变虚。交给浏览器按当前 transform 重新光栅化。
   */
  transform-origin: 0 0;
}

.seat-map__floor {
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(420px 260px at 33% 28%, color-mix(in srgb, var(--ssr-surface) 78%, transparent), transparent 72%),
    linear-gradient(160deg, var(--ssr-surface) 0%, var(--ssr-bg) 100%);
  border: 1px solid var(--ssr-line-strong);
  border-radius: 27px;
  box-shadow:
    0 26px 60px -36px var(--ssr-line-strong),
    inset 0 0 0 1px var(--ssr-surface);
}

.seat-map__floor::before {
  position: absolute;
  inset: 0;
  content: '';
  background-image:
    linear-gradient(to right, color-mix(in srgb, var(--ssr-desk-line) 8%, transparent) 1px, transparent 1px),
    linear-gradient(to bottom, color-mix(in srgb, var(--ssr-desk-line) 8%, transparent) 1px, transparent 1px);
  background-size: 20px 20px;
  mask-image: radial-gradient(120% 100% at 50% 40%, #000 40%, transparent 100%);
  pointer-events: none;
}

.seat-map__arch {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.arch-wall {
  fill: none;
  stroke: var(--ssr-line-strong);
  stroke-width: 2.4;
}

.arch-window {
  fill: none;
  stroke: var(--ssr-success);
  stroke-width: 2;
}

.arch-window--faint {
  opacity: 0.42;
}

.arch-window-tick {
  stroke: color-mix(in srgb, var(--ssr-success) 42%, transparent);
  stroke-width: 1;
}

.arch-divider {
  fill: none;
  stroke: var(--ssr-line);
  stroke-width: 1;
  stroke-dasharray: 3 5;
}

.arch-door {
  fill: none;
  stroke: var(--ssr-line-strong);
  stroke-width: 1.2;
}

.arch-door-arc {
  fill: none;
  stroke: var(--ssr-line-strong);
  stroke-width: 1.2;
}

.arch-aisle {
  fill: none;
  stroke: color-mix(in srgb, var(--ssr-primary) 28%, transparent);
  stroke-width: 1.2;
  stroke-dasharray: 2 7;
}

.arch-scale {
  fill: none;
  stroke: var(--ssr-muted-ink);
  stroke-width: 1;
}

.arch-label {
  fill: var(--ssr-muted-ink);
  font-family: var(--ssr-font-mono, monospace);
  font-size: 8px;
  letter-spacing: 0.08em;
}

.arch-label[text-anchor='middle'] {
  text-anchor: middle;
}

.map-zone {
  position: absolute;
  z-index: 2;
  border: 1px dashed color-mix(in srgb, var(--ssr-line-strong) 54%, transparent);
  border-radius: 18px;
  background: color-mix(in srgb, var(--ssr-primary) 2%, transparent);
  pointer-events: none;
}

.map-zone--window {
  background: color-mix(in srgb, var(--ssr-success) 2%, transparent);
}

.map-zone--quiet {
  background: color-mix(in srgb, var(--ssr-muted-ink) 2%, transparent);
}

.map-zone--power {
  background: color-mix(in srgb, var(--ssr-warning) 2%, transparent);
}

.map-zone--pair {
  background: color-mix(in srgb, var(--ssr-warning) 2%, transparent);
}

.map-zone__label {
  position: absolute;
  top: 8px;
  left: 10px;
  display: flex;
  gap: 5px;
  align-items: baseline;
  color: var(--ssr-muted-ink);
  font-family: var(--ssr-font-mono, monospace);
  font-size: var(--table-font, 8px);
  line-height: 1.2;
  white-space: nowrap;
}

.map-zone__label strong {
  color: var(--ssr-ink);
  font-family: var(--ssr-font-display, inherit);
  font-size: calc(var(--table-font, 8px) * 1.08);
  font-style: italic;
  font-weight: 600;
}

.map-zone__label em {
  font-style: normal;
  opacity: 0.72;
}

.map-table {
  position: absolute;
  z-index: 3;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1px;
  overflow: hidden;
  /* 桌面文字用墨色压深一档：原来是桌线色配桌面色，缩放后整行看着发灰、像糊了 */
  color: color-mix(in srgb, var(--ssr-ink) 82%, var(--ssr-desk-line));
  background:
    repeating-linear-gradient(90deg, transparent 0 8px, color-mix(in srgb, var(--ssr-desk-line) 7%, transparent) 8px 9px),
    linear-gradient(180deg, var(--ssr-desk-top) 0%, var(--ssr-desk-mid) 100%);
  border: 1px solid var(--ssr-desk-line);
  border-radius: 6px;
  box-shadow:
    0 4px 0 var(--ssr-desk-bottom),
    0 8px 14px -10px color-mix(in srgb, var(--ssr-desk-line) 60%, transparent);
  transition:
    filter 140ms ease,
    border-color 140ms ease,
    box-shadow 140ms ease;
}

.map-table--capsule {
  border-radius: 999px;
}

.map-table--round {
  border-radius: 50%;
}

.map-table.is-hovered {
  filter: brightness(1.035);
  border-color: color-mix(in srgb, var(--ssr-primary) 42%, var(--ssr-desk-line));
}

.map-table.is-selected {
  border-color: var(--ssr-primary);
  border-width: 2px;
  box-shadow:
    0 0 0 2px var(--ssr-surface),
    0 0 0 4px var(--ssr-primary),
    0 4px 0 var(--ssr-desk-bottom),
    0 10px 20px -10px color-mix(in srgb, var(--ssr-primary) 46%, transparent);
}

.map-table__label {
  position: relative;
  z-index: 1;
  display: flex;
  gap: 3px;
  align-items: center;
  font-family: var(--ssr-font-mono, monospace);
  font-size: var(--table-font, 8px);
  line-height: 1;
}

.map-table__label strong {
  font-weight: 600;
}

.map-table__tag {
  padding: 0 2px;
  color: color-mix(in srgb, var(--ssr-ink) 70%, var(--ssr-desk-line));
  border: 1px solid color-mix(in srgb, var(--ssr-desk-line) 55%, transparent);
  border-radius: 2px;
  font-family: var(--ssr-font-ui, sans-serif);
  font-size: 0.82em;
}

.map-table__meta {
  position: relative;
  z-index: 1;
  color: color-mix(in srgb, var(--ssr-ink) 62%, var(--ssr-desk-line));
  font-family: var(--ssr-font-ui, sans-serif);
  font-size: calc(var(--table-font, 8px) * 0.86);
  line-height: 1.1;
}

.map-chair {
  position: absolute;
  z-index: 5;
  display: block;
  padding: 0;
  cursor: pointer;
  background: transparent;
  border: 0;
  border-radius: 0;
  -webkit-tap-highlight-color: transparent;
}

.map-chair::before {
  position: absolute;
  inset: -5px;
  content: '';
  border-radius: 10px;
}

.map-chair__back {
  position: absolute;
  z-index: 2;
  background: var(--ssr-desk-mid);
  border: 1px solid var(--ssr-desk-line);
  box-shadow: 0 1px 2px color-mix(in srgb, var(--ssr-desk-line) 24%, transparent);
}

.map-chair--n .map-chair__back {
  top: -6px;
  left: 9%;
  width: 82%;
  height: 8px;
  border-radius: 999px 999px 3px 3px;
}

.map-chair--s .map-chair__back {
  bottom: -6px;
  left: 9%;
  width: 82%;
  height: 8px;
  border-radius: 3px 3px 999px 999px;
}

.map-chair--w .map-chair__back {
  top: 9%;
  left: -6px;
  width: 8px;
  height: 82%;
  border-radius: 999px 3px 3px 999px;
}

.map-chair--e .map-chair__back {
  top: 9%;
  right: -6px;
  width: 8px;
  height: 82%;
  border-radius: 3px 999px 999px 3px;
}

.map-chair__pad {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
  align-items: center;
  justify-content: center;
  overflow: visible;
  color: var(--chair-fg, var(--ssr-success));
  background: var(--chair-bg, var(--ssr-success-bg));
  border: 1.4px solid var(--chair-line, var(--ssr-success));
  box-shadow:
    0 3px 0 color-mix(in srgb, var(--ssr-desk-bottom) 72%, transparent),
    0 5px 9px -7px color-mix(in srgb, var(--ssr-desk-line) 44%, transparent);
  transition:
    transform 140ms ease,
    filter 140ms ease,
    box-shadow 140ms ease;
}

.map-chair--n .map-chair__pad {
  border-radius: 13px 13px 7px 7px;
}

.map-chair--s .map-chair__pad {
  border-radius: 7px 7px 13px 13px;
}

.map-chair--e .map-chair__pad {
  border-radius: 7px 13px 13px 7px;
}

.map-chair--w .map-chair__pad {
  border-radius: 13px 7px 7px 13px;
}

.map-chair__no {
  font-family: var(--ssr-font-mono, monospace);
  font-size: var(--chair-font, 9px);
  font-weight: 600;
  letter-spacing: -0.06em;
  line-height: 1;
  white-space: nowrap;
}

.map-chair__no-short {
  display: none;
}

.seat-map__stage[data-lod='far'] .map-chair__no-full {
  display: none;
}

.seat-map__stage[data-lod='far'] .map-chair__no-short {
  display: inline;
}

.map-chair__state {
  position: absolute;
  right: 2px;
  bottom: 2px;
  display: inline-grid;
  width: 10px;
  height: 10px;
  color: var(--chair-line, var(--ssr-success));
  background: color-mix(in srgb, var(--ssr-surface) 86%, transparent);
  border-radius: 50%;
  place-items: center;
}

.map-chair__state .el-icon {
  font-size: 7px;
}

.map-chair__mine {
  position: absolute;
  top: -9px;
  left: 50%;
  z-index: 4;
  padding: 1px 3px;
  color: var(--ssr-on-primary);
  background: var(--ssr-warning);
  border-radius: 3px;
  font-family: var(--ssr-font-ui, sans-serif);
  font-size: 6px;
  font-weight: 600;
  line-height: 1.4;
  white-space: nowrap;
  transform: translateX(-50%);
}

/* 地图状态色直接复用全局座位图例 token（与 Toolbar / 列表完全同色） */
.map-chair--free {
  --chair-bg: var(--ssr-seat-free-bg);
  --chair-line: var(--ssr-seat-free-line);
  --chair-fg: var(--ssr-seat-free-fg);
}

.map-chair--taken {
  --chair-bg: var(--ssr-seat-taken-bg);
  --chair-line: var(--ssr-seat-taken-line);
  --chair-fg: var(--ssr-seat-taken-fg);
}

.map-chair--taken .map-chair__pad {
  background:
    repeating-linear-gradient(
      45deg,
      transparent 0 3px,
      var(--ssr-seat-taken-hatch) 3px 6px
    ),
    var(--chair-bg);
  border-style: dashed;
}

.map-chair--unknown {
  --chair-bg: var(--ssr-bg);
  --chair-line: var(--ssr-line-strong);
  --chair-fg: var(--ssr-muted-ink);
}

.map-chair--unknown .map-chair__pad {
  border-style: double;
}

.map-chair--closed {
  --chair-bg: var(--ssr-warning-bg);
  --chair-line: var(--ssr-warning);
  --chair-fg: var(--ssr-warning-ink);
}

.map-chair--closed .map-chair__pad {
  border-style: dotted;
}

.map-chair--fix {
  --chair-bg: var(--ssr-seat-fix-bg);
  --chair-line: var(--ssr-seat-fix-line);
  --chair-fg: var(--ssr-seat-fix-fg);
}

.map-chair--fix .map-chair__pad {
  background:
    repeating-linear-gradient(
      -45deg,
      transparent 0 2px,
      var(--ssr-seat-fix-hatch) 2px 5px
    ),
    var(--chair-bg);
}

.map-chair--off {
  --chair-bg: var(--ssr-seat-off-bg);
  --chair-line: var(--ssr-seat-off-line);
  --chair-fg: var(--ssr-seat-off-fg);
}

.map-chair--off .map-chair__pad {
  border-style: dotted;
}

.map-chair--mine {
  --chair-bg: var(--ssr-warning-bg);
  --chair-line: var(--ssr-warning);
  --chair-fg: var(--ssr-warning-ink);
}

.map-chair--mine .map-chair__pad {
  border-style: double;
  border-width: 2px;
}

.map-chair--table-hover .map-chair__pad,
.map-chair:hover .map-chair__pad {
  filter: brightness(1.025);
  transform: translateY(-1px);
  box-shadow:
    0 0 0 2px color-mix(in srgb, var(--ssr-primary) 10%, transparent),
    0 4px 0 color-mix(in srgb, var(--ssr-desk-bottom) 72%, transparent),
    0 8px 14px -8px color-mix(in srgb, var(--ssr-desk-line) 50%, transparent);
}

.map-chair--selected .map-chair__pad {
  border-color: var(--ssr-primary);
  transform: translateY(-1px);
  box-shadow:
    0 0 0 2px var(--ssr-surface),
    0 0 0 4px var(--ssr-primary),
    0 0 18px 3px color-mix(in srgb, var(--ssr-primary) 22%, transparent),
    0 4px 0 color-mix(in srgb, var(--ssr-desk-bottom) 72%, transparent);
}

.map-chair--selected::after {
  position: absolute;
  top: -8px;
  right: -8px;
  z-index: 6;
  display: grid;
  width: 15px;
  height: 15px;
  color: var(--ssr-on-primary);
  content: '✓';
  background: var(--ssr-primary);
  border: 2px solid var(--ssr-surface);
  border-radius: 50%;
  font-size: 7px;
  font-weight: 700;
  place-items: center;
}

/* 不符合当前筛选：保留椅子原位，只用低透明度虚线占位，不响应点击 */
.map-chair--filtered {
  cursor: default;
  opacity: 0.42;
  filter: grayscale(1);
}

.map-chair--filtered .map-chair__back {
  opacity: 0.55;
}

.map-chair--filtered .map-chair__pad,
.map-chair--filtered:hover .map-chair__pad {
  background: transparent;
  border-color: var(--ssr-line-strong);
  border-style: dashed;
  box-shadow: none;
  filter: none;
  transform: none;
}

.map-chair:focus-visible {
  outline: none;
}

.map-chair:focus-visible .map-chair__pad {
  outline: 2px solid var(--ssr-primary);
  outline-offset: 3px;
}

.map-chair:active .map-chair__pad {
  transform: translateY(1px) scale(0.98);
}

.map-front-desk {
  position: absolute;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 1px;
  align-items: center;
  justify-content: center;
  width: 148px;
  height: 62px;
  color: var(--ssr-muted-ink);
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line-strong);
  border-radius: 9px;
  box-shadow: 0 4px 0 color-mix(in srgb, var(--ssr-line-strong) 55%, transparent);
}

.map-front-desk strong {
  color: var(--ssr-ink);
  font-family: var(--ssr-font-ui, sans-serif);
  font-size: 10px;
  font-weight: 600;
}

.map-front-desk span {
  font-family: var(--ssr-font-mono, monospace);
  font-size: 7px;
  letter-spacing: 0.08em;
}

.seat-hover {
  position: absolute;
  z-index: 9;
  display: flex;
  gap: 7px;
  align-items: baseline;
  padding: 5px 10px;
  color: var(--ssr-ink);
  white-space: nowrap;
  pointer-events: none;
  background: var(--ssr-surface-raised);
  border: 1px solid var(--ssr-line-strong);
  border-radius: 10px;
  box-shadow: var(--ssr-shadow-md);
  transform: translate(-50%, calc(-100% - 8px));
  font-size: var(--ssr-font-note);
}

.seat-hover--below {
  transform: translate(-50%, 10px);
}

.seat-hover__no {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.seat-hover__state {
  color: var(--ssr-muted-ink);
}

.seat-hover__state--mine {
  color: var(--ssr-primary-ink);
  font-weight: 600;
}

.seat-hover__meta {
  color: var(--ssr-muted-ink);
}

.seat-map__hint {
  position: absolute;
  right: 50%;
  bottom: 10px;
  z-index: 8;
  display: flex;
  gap: 9px;
  padding: 4px 8px;
  margin: 0;
  color: var(--ssr-muted-ink);
  background: color-mix(in srgb, var(--ssr-surface) 86%, transparent);
  border: 1px solid var(--ssr-line);
  border-radius: 999px;
  font-size: 9px;
  white-space: nowrap;
  transform: translateX(50%);
  pointer-events: none;
  backdrop-filter: blur(8px);
}

.seat-map__hint span + span::before {
  margin-right: 9px;
  content: '·';
}

/* 缩略导航：整图轮廓 + 当前视野框，可点击 / 拖动跳转。
   放在画布右上角——底部常被搜索条拦着，放下面会被裁掉一半。 */
.seat-mini {
  position: absolute;
  top: 12px;
  right: 12px;
  z-index: 9;
  overflow: hidden;
  cursor: pointer;
  background: color-mix(in srgb, var(--ssr-surface) 92%, transparent);
  border: 1px solid var(--ssr-line-strong);
  border-radius: 10px;
  box-shadow: var(--ssr-shadow-md);
  touch-action: none;
}

.seat-mini__svg {
  display: block;
  width: 100%;
  height: 100%;
}

.seat-mini__zone {
  fill: color-mix(in srgb, var(--ssr-bg) 70%, transparent);
  stroke: var(--ssr-line);
  stroke-width: 4;
}

.seat-mini__table {
  fill: var(--ssr-desk-mid, var(--ssr-line-strong));
  opacity: 0.55;
}

.seat-mini__view {
  fill: color-mix(in srgb, var(--ssr-primary) 16%, transparent);
  stroke: var(--ssr-primary);
  stroke-width: 8;
}

.seat-map__stage[data-lod='far'] .map-table__meta,
.seat-map__stage[data-lod='far'] .map-table__tag,
.seat-map__stage[data-lod='far'] .map-zone__label em,
.seat-map__stage[data-lod='far'] .map-chair__mine {
  display: none;
}

@media (max-width: 720px) {
  .seat-map__shell {
    height: 430px;
  }

  .seat-map__hint {
    display: none;
  }

  .map-table__tag {
    display: none;
  }

  .map-zone__label em {
    display: none;
  }
}
</style>
