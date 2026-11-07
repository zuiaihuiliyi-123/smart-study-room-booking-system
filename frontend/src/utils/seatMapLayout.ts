/**
 * 预约地图的「桌椅布局适配层」。
 *
 * 后端座位目前只有 area_id / seat_no / seat_type / has_power / near_window，没有 x/y。
 * 因此本文件在**前端只读数据**上生成一套可复现的家具布局：
 * - 分区 → 房间区域（按分区名称或座位属性推断区域类型）
 * - 座位 → 椅子，按类型分组成 2/4 人桌
 * - 生成桌子、椅子、区域、房间外框所需的几何数据
 *
 * 这是一层可替换的适配器：后续后端提供 layout 接口时，只需把 buildSeatMapLayout
 * 的数据源替换为接口返回值，地图组件和预约逻辑不需要改。
 */
import type { Area } from '@/types'
import type { MatrixCell, MatrixGroup } from '@/components/booking/types'

export type MapZoneKind = 'window' | 'quiet' | 'power' | 'pair' | 'accessible' | 'central'
export type ChairOrientation = 'n' | 's' | 'e' | 'w'

export interface SeatMapZone {
  id: string
  label: string
  en: string
  kind: MapZoneKind
  x: number
  y: number
  w: number
  h: number
}

export interface SeatMapTable {
  id: string
  zoneId: string
  label: string
  kind: MapZoneKind
  shape: 'rect' | 'capsule' | 'round'
  x: number
  y: number
  w: number
  h: number
  meta: string
  tags: string[]
}

export interface SeatMapChair {
  key: number
  cell: MatrixCell
  tableId: string
  x: number
  y: number
  w: number
  h: number
  orientation: ChairOrientation
}

export interface SeatMapLayout {
  width: number
  height: number
  zones: SeatMapZone[]
  tables: SeatMapTable[]
  chairs: SeatMapChair[]
  hasWindow: boolean
}

const KIND_META: Record<MapZoneKind, { label: string; en: string }> = {
  window: { label: '窗边静区', en: 'WINDOW QUIET' },
  quiet: { label: '静音角', en: 'SILENT NOOK' },
  power: { label: '电源长桌', en: 'POWER BAR' },
  pair: { label: '双人研习舱', en: 'PAIR POD' },
  accessible: { label: '无障碍位', en: 'ACCESS' },
  central: { label: '中央开放区', en: 'OPEN DESK' },
}

const CHAIR_W = 28
const CHAIR_H = 24
const ROW_GAP = 10
const ZONE_PAD = 12
const ZONE_TOP = 36

interface TableBlueprint {
  table: Omit<SeatMapTable, 'id' | 'zoneId' | 'label' | 'kind'>
  chairs: Array<{
    cell: MatrixCell
    dx: number
    dy: number
    orientation: ChairOrientation
  }>
  w: number
  h: number
}

function inferKind(name: string, cells: readonly MatrixCell[]): MapZoneKind {
  if (/窗|window/i.test(name)) return 'window'
  if (/静|安静|quiet/i.test(name)) return 'quiet'
  if (/电源|插座|power/i.test(name)) return 'power'
  if (/双人|研习|pair/i.test(name)) return 'pair'
  if (/无障碍|access/i.test(name)) return 'accessible'
  if (/标准|开放|central/i.test(name)) return 'central'

  const nearWindow = cells.filter((cell) => cell.seat.near_window).length
  if (nearWindow > cells.length / 2) return 'window'
  const power = cells.filter((cell) => cell.seat.has_power).length
  if (power > cells.length / 2) return 'power'
  return 'central'
}

function zoneLabel(group: MatrixGroup, areas: readonly Area[], kind: MapZoneKind): string {
  const name = areas.find((area) => String(area.id) === group.key)?.name?.trim()
  return name || KIND_META[kind].label
}

function tableTags(kind: MapZoneKind, cells: readonly MatrixCell[]): string[] {
  const tags = new Set<string>()
  if (kind === 'window' || cells.some((cell) => cell.seat.near_window)) tags.add('窗')
  if (kind === 'power' || cells.some((cell) => cell.seat.has_power)) tags.add('电')
  if (kind === 'quiet') tags.add('静')
  if (kind === 'pair') tags.add('双')
  if (kind === 'accessible') tags.add('无')
  if (cells.some((cell) => /VIP|长时段/i.test(cell.seat.seat_type))) tags.add('★')
  return [...tags].slice(0, 3)
}

function chunkCells(cells: readonly MatrixCell[], capacity: number): MatrixCell[][] {
  const chunks: MatrixCell[][] = []
  let rest = [...cells]
  while (rest.length > 0) {
    let size = Math.min(capacity, rest.length)
    if (rest.length - size === 1 && size > 2) size -= 1
    chunks.push(rest.slice(0, size))
    rest = rest.slice(size)
  }
  return chunks
}

function horizontalBlueprint(cells: readonly MatrixCell[], kind: MapZoneKind): TableBlueprint {
  const count = cells.length
  const tableW = Math.max(74, count * 34 + 8)
  const tableH = count <= 2 ? 38 : 42
  const topCount = Math.ceil(count / 2)
  const bottomCount = count - topCount
  const tableY = CHAIR_H + 4
  const chairs: TableBlueprint['chairs'] = []

  for (let i = 0; i < topCount; i += 1) {
    chairs.push({
      cell: cells[i],
      dx: ((i + 0.5) * tableW) / topCount - CHAIR_W / 2,
      dy: 0,
      orientation: 'n',
    })
  }
  for (let i = 0; i < bottomCount; i += 1) {
    chairs.push({
      cell: cells[topCount + i],
      dx: ((i + 0.5) * tableW) / bottomCount - CHAIR_W / 2,
      dy: tableY + tableH + 4,
      orientation: 's',
    })
  }

  return {
    table: {
      shape: kind === 'accessible' ? 'capsule' : 'rect',
      x: 0,
      y: tableY,
      w: tableW,
      h: tableH,
      meta: `${count} 座`,
      tags: tableTags(kind, cells),
    },
    chairs,
    w: tableW,
    h: tableY + tableH + 4 + CHAIR_H,
  }
}

function verticalPowerBlueprint(cells: readonly MatrixCell[]): TableBlueprint {
  const count = cells.length
  const tableH = Math.max(96, count * 34)
  const tableW = 52
  const leftCount = Math.ceil(count / 2)
  const rightCount = count - leftCount
  const tableX = CHAIR_W + 6
  const chairs: TableBlueprint['chairs'] = []

  for (let i = 0; i < leftCount; i += 1) {
    chairs.push({
      cell: cells[i],
      dx: 0,
      dy: ((i + 0.5) * tableH) / leftCount - CHAIR_H / 2,
      orientation: 'w',
    })
  }
  for (let i = 0; i < rightCount; i += 1) {
    chairs.push({
      cell: cells[leftCount + i],
      dx: tableX + tableW + 6,
      dy: ((i + 0.5) * tableH) / rightCount - CHAIR_H / 2,
      orientation: 'e',
    })
  }

  return {
    table: {
      shape: 'rect',
      x: tableX,
      y: 0,
      w: tableW,
      h: tableH,
      meta: `${count} 座 · 长桌`,
      tags: tableTags('power', cells),
    },
    chairs,
    w: tableX + tableW + 6 + CHAIR_W,
    h: tableH,
  }
}

function roundTableBlueprint(cells: readonly MatrixCell[]): TableBlueprint {
  const tableW = 58
  const tableH = 52
  const centerX = 60
  const centerY = 56
  const radius = 43
  const tableX = centerX - tableW / 2
  const tableY = centerY - tableH / 2
  const chairs: TableBlueprint['chairs'] = cells.map((cell, index) => {
    const angle = -Math.PI / 2 + (index * Math.PI * 2) / Math.max(cells.length, 1)
    const cos = Math.cos(angle)
    const sin = Math.sin(angle)
    const px = centerX + cos * radius
    const py = centerY + sin * radius
    const orientation: ChairOrientation = sin < -0.38 ? 'n' : sin > 0.38 ? 's' : cos > 0 ? 'e' : 'w'
    return {
      cell,
      dx: px - CHAIR_W / 2,
      dy: py - CHAIR_H / 2,
      orientation,
    }
  })
  return {
    table: {
      shape: 'round',
      x: tableX,
      y: tableY,
      w: tableW,
      h: tableH,
      meta: `${cells.length} 座`,
      tags: tableTags('quiet', cells),
    },
    chairs,
    w: 120,
    h: 112,
  }
}

function accessibleBlueprint(cells: readonly MatrixCell[]): TableBlueprint {
  const tableW = 142
  const tableH = 34
  const chairs: TableBlueprint['chairs'] = cells.map((cell, index) => ({
    cell,
    dx: ((index + 0.5) * tableW) / cells.length - CHAIR_W / 2,
    dy: tableH + 8,
    orientation: 's',
  }))
  return {
    table: {
      shape: 'capsule',
      x: 0,
      y: 0,
      w: tableW,
      h: tableH,
      meta: `${cells.length} 座 · 宽敞`,
      tags: tableTags('accessible', cells),
    },
    chairs,
    w: tableW,
    h: tableH + 8 + CHAIR_H,
  }
}

function makeBlueprint(kind: MapZoneKind, cells: readonly MatrixCell[]): TableBlueprint {
  if (kind === 'power') return verticalPowerBlueprint(cells)
  if (kind === 'quiet') return roundTableBlueprint(cells)
  if (kind === 'accessible') return accessibleBlueprint(cells)
  return horizontalBlueprint(cells, kind)
}

function capacityFor(kind: MapZoneKind): number {
  if (kind === 'pair' || kind === 'accessible' || kind === 'central') return 2
  return 4
}

function tablePrefix(group: MatrixGroup, fallback: number): string {
  const first = group.cells[0]?.seat.seat_no ?? ''
  const prefix = first.split('-')[0]?.trim().toUpperCase() ?? ''
  return /^[A-Z]{1,3}$/.test(prefix) ? prefix : `T${fallback}`
}

function placeGroup(
  group: MatrixGroup,
  zone: SeatMapZone,
  kind: MapZoneKind,
  fallbackIndex: number,
): { tables: SeatMapTable[]; chairs: SeatMapChair[] } {
  const capacity = capacityFor(kind)
  const chunks = capacity > 0 ? chunkCells(group.cells, capacity) : [group.cells]
  const blueprints = chunks.map((cells) => makeBlueprint(kind, cells))
  const prefix = tablePrefix(group, fallbackIndex)
  const placed: Array<{ blueprint: TableBlueprint; ox: number; oy: number }> = []
  let cursorX = zone.x + ZONE_PAD
  let cursorY = zone.y + ZONE_TOP
  let rowHeight = 0
  let rowStartX = cursorX
  let rowItems: Array<{ blueprint: TableBlueprint; ox: number; oy: number }> = []
  const rows: Array<{ startX: number; width: number; items: typeof rowItems }> = []

  const finishRow = () => {
    if (rowItems.length === 0) return
    const width = rowItems.reduce((sum, item) => sum + item.blueprint.w, 0) + (rowItems.length - 1) * ROW_GAP
    rows.push({ startX: rowStartX, width, items: [...rowItems] })
    rowItems = []
  }

  for (const blueprint of blueprints) {
    if (rowItems.length > 0 && cursorX + blueprint.w > zone.x + zone.w - ZONE_PAD) {
      finishRow()
      cursorX = zone.x + ZONE_PAD
      rowStartX = cursorX
      cursorY += rowHeight + ROW_GAP
      rowHeight = 0
    }
    const item = { blueprint, ox: cursorX, oy: cursorY }
    placed.push(item)
    rowItems.push(item)
    cursorX += blueprint.w + ROW_GAP
    rowHeight = Math.max(rowHeight, blueprint.h)
  }
  finishRow()

  /* 行内水平居中，整组垂直居中，让少量桌椅不会贴着区域左上角 */
  rows.forEach((row) => {
    const delta = zone.x + zone.w / 2 - (row.startX + row.width / 2)
    if (Math.abs(delta) > 0.1) {
      row.items.forEach((item) => {
        item.ox += delta
      })
    }
  })
  const totalHeight = placed.length
    ? Math.max(...placed.map((item) => item.oy + item.blueprint.h)) - Math.min(...placed.map((item) => item.oy))
    : 0
  const availableHeight = zone.h - ZONE_TOP - 10
  const verticalDelta = totalHeight > 0 && totalHeight < availableHeight
    ? (availableHeight - totalHeight) / 2
    : 0

  const tables: SeatMapTable[] = []
  const chairs: SeatMapChair[] = []
  placed.forEach((item, tableIndex) => {
    const { blueprint } = item
    const oy = item.oy + verticalDelta
    const tableId = `${group.key}-${tableIndex}`
    tables.push({
      id: tableId,
      zoneId: group.key,
      label: `${prefix}${tableIndex + 1}`,
      kind,
      ...blueprint.table,
      x: item.ox + blueprint.table.x,
      y: oy + blueprint.table.y,
    })
    blueprint.chairs.forEach((chair) => {
      chairs.push({
        key: chair.cell.seat.id,
        cell: chair.cell,
        tableId,
        x: item.ox + chair.dx,
        y: oy + chair.dy,
        w: CHAIR_W,
        h: CHAIR_H,
        orientation: chair.orientation,
      })
    })
  })
  return { tables, chairs }
}

export function buildSeatMapLayout(
  groups: readonly MatrixGroup[],
  areas: readonly Area[] = [],
): SeatMapLayout {
  const usableGroups = groups.filter((group) => group.cells.length > 0)
  if (usableGroups.length === 0) {
    return { width: 760, height: 580, zones: [], tables: [], chairs: [], hasWindow: false }
  }

  const count = usableGroups.length
  const width = count <= 2 ? 760 : count <= 4 ? 900 : count <= 6 ? 1020 : 1160
  const height = count <= 2 ? 580 : count <= 4 ? 640 : count <= 6 ? 720 : 820
  const columns = count <= 1 ? 1 : count <= 4 ? 2 : count <= 6 ? 3 : 4
  const rows = Math.ceil(count / columns)
  const inner = { x: 42, y: 56, w: width - 84, h: height - 156 }
  const gap = 14
  const zoneW = (inner.w - gap * (columns - 1)) / columns
  const zoneH = (inner.h - gap * (rows - 1)) / rows

  const zones: SeatMapZone[] = []
  const tables: SeatMapTable[] = []
  const chairs: SeatMapChair[] = []

  usableGroups.forEach((group, index) => {
    const col = index % columns
    const row = Math.floor(index / columns)
    const x = inner.x + col * (zoneW + gap)
    const y = inner.y + row * (zoneH + gap)
    const areaName = areas.find((area) => String(area.id) === group.key)?.name ?? ''
    const kind = inferKind(areaName || group.title, group.cells)
    const zone: SeatMapZone = {
      id: group.key,
      label: zoneLabel(group, areas, kind),
      en: KIND_META[kind].en,
      kind,
      x,
      y,
      w: zoneW,
      h: zoneH,
    }
    zones.push(zone)
    const placed = placeGroup(group, zone, kind, index + 1)
    tables.push(...placed.tables)
    chairs.push(...placed.chairs)
  })

  return {
    width,
    height,
    zones,
    tables,
    chairs,
    hasWindow: zones.some((zone) => zone.kind === 'window')
      || groups.some((group) => group.cells.some((cell) => cell.seat.near_window)),
  }
}
