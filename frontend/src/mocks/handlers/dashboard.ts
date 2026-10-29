/**
 * 数据看板 mock：GET /dashboard/overview、/dashboard/seat-usage、/dashboard/trend。
 *
 * 职责：按 FR-050～FR-052 本版口径返回**聚合结果**（IR-004：看板只能用聚合值）。
 * 三处口径：
 * - 概览：① 座位总数 = "可用"座位数（不含维修中/停用）；② 使用中预约数 = 查询时刻处于"使用中"
 *   的预约单（**不是**座位状态）；③ 今日预约 = 当日 [00:00,24:00) 创建且未取消；④ 今日违约 =
 *   当日产生的违约记录；⑤ 受限账户 = 账户状态"受限"的用户数（账户不归属自习室，恒为全局口径）。
 * - 柱状图（`group_by=slot`，图 1）：各自习室各时段座位占用率 = 被有效预约覆盖的 30 分钟座位块数 /
 *   容量（座位数 × 时段块数 × 天数）。缺省 `group_by=seat` 时退回 FR-050 原文口径
 *   （各座位已使用时段数），供口径对照。
 * - 折线图：按自然日的"当日创建且未取消"预约数与"当日产生"的违约数。
 *
 * 统计范围：`room_id` 可选；缺省为全部自习室（BR-018 的授权收窄由后端负责）。
 * 参数非法 / 自习室不存在一律 400 / 404，便于前端验证"失败保留旧数据"。
 */
import { http } from 'msw'

import type { ChartItem, SeatUsageSlotRow, StatOverview, TrendPoint } from '@/types'

import { getDb, seatLabel, type MockDb } from '../db'
import { abort, json, requireAdmin, safe, strParam } from '../http'
import {
  addDays,
  dayDiff,
  formatDate,
  minutesOfDay,
  parseDate,
  parseTimeMinutes,
  serverNow,
} from '../time'

const MAX_TREND_DAYS = 31
const SLOT_MINUTES = 30

/** 图 1 的时段桶（左闭右开，与原型 UC-14 的 08-10 / 10-12 … 对齐） */
const SLOT_BUCKETS: { label: string; start: number; end: number }[] = [
  { label: '08:00-10:00', start: 8 * 60, end: 10 * 60 },
  { label: '10:00-12:00', start: 10 * 60, end: 12 * 60 },
  { label: '12:00-14:00', start: 12 * 60, end: 14 * 60 },
  { label: '14:00-16:00', start: 14 * 60, end: 16 * 60 },
  { label: '16:00-18:00', start: 16 * 60, end: 18 * 60 },
  { label: '18:00-20:00', start: 18 * 60, end: 20 * 60 },
  { label: '20:00-22:00', start: 20 * 60, end: 22 * 60 },
]

/** 占用座位时段的预约状态：已取消 / 已违约不占用（AGENTS §4「有效预约」） */
const OCCUPIED_STATUS = new Set(['待使用', '使用中', '已完成'])

interface Range {
  startDate: string
  endDate: string
  /** null = 全部自习室 */
  roomId: number | null
}

function createdAtDay(createdAt: string): string {
  return createdAt.slice(0, 10)
}

function durationSlots(startTime: string, endTime: string): number {
  const start = parseTimeMinutes(startTime) ?? 0
  const end = parseTimeMinutes(endTime) ?? 0
  return end > start ? (end - start) / SLOT_MINUTES : 0
}

/** 范围过滤：座位 → 预约 → 违约 三级向下收窄 */
function scopeOf(db: MockDb, roomId: number | null) {
  const seats = roomId === null ? db.seats : db.seats.filter((seat) => seat.room_id === roomId)
  const seatIds = new Set(seats.map((seat) => seat.id))
  const reservations =
    roomId === null
    ? db.reservations
    : db.reservations.filter((record) => seatIds.has(record.seat_id))
  const reservationIds = new Set(reservations.map((record) => record.id))
  const violations =
    roomId === null
    ? db.violations
    : db.violations.filter((record) => reservationIds.has(record.reservation_id))
  return { seats, seatIds, reservations, violations }
}

function overviewOf(db: MockDb, roomId: number | null): StatOverview {
  const now = serverNow()
  const today = formatDate(now)
  const minutes = minutesOfDay(now)
  const { seats, reservations, violations } = scopeOf(db, roomId)

  return {
    seat_total: seats.filter((seat) => seat.status === '可用').length,
    in_use: reservations.filter((record) => {
      if (record.status !== '使用中' || record.reserve_date !== today) return false
      const start = parseTimeMinutes(record.start_time) ?? 0
      const end = parseTimeMinutes(record.end_time) ?? 0
      return start <= minutes && minutes < end
    }).length,
  today_reservations: reservations.filter(
    (record) => createdAtDay(record.created_at) === today && record.status !== '已取消',
  ).length,
  today_violations: violations.filter((record) => createdAtDay(record.created_at) === today)
    .length,
  // ⑤ 账户不归属自习室：按自习室筛选时仍保持全局口径（页面注脚已写明）
  restricted_accounts: db.users.filter((user) => user.account_status === '受限').length,
}
}

/** FR-050 原文口径：各座位在统计周期内的已使用时段数（含 0 值，按值倒序） */
function seatUsageOf(db: MockDb, range: Range): ChartItem[] {
  const slots = new Map<number, number>()
  for (const record of db.reservations) {
    if (record.status !== '已完成') continue
    if (record.reserve_date < range.startDate || record.reserve_date > range.endDate) continue
    const count = durationSlots(record.start_time, record.end_time)
    if (count <= 0) continue
    slots.set(record.seat_id, (slots.get(record.seat_id) ?? 0) + count)
  }

  return db.seats
    .filter((seat) => range.roomId === null || seat.room_id === range.roomId)
    .map((seat) => ({ name: seatLabel(seat.id), value: slots.get(seat.id) ?? 0 }))
    .sort((left, right) => {
    if (right.value !== left.value) return right.value - left.value
    return left.name < right.name ? -1 : left.name > right.name ? 1 : 0
  })
}

/** 图 1：各自习室各时段座位占用率（行的容量口径见 `SeatUsageSlotRow` 注释） */
function slotOccupancyOf(db: MockDb, range: Range): SeatUsageSlotRow[] {
  const start = parseDate(range.startDate)
  const end = parseDate(range.endDate)
  if (!start || !end) return []
  const days = dayDiff(start, end) + 1
  const rooms = db.rooms.filter((room) => range.roomId === null || room.id === range.roomId)
  const rows: SeatUsageSlotRow[] = []

  for (const room of rooms) {
    const seats = db.seats.filter((seat) => seat.room_id === room.id)
    const seatIds = new Set(seats.map((seat) => seat.id))
    const records = db.reservations.filter(
      (record) =>
          seatIds.has(record.seat_id) &&
          OCCUPIED_STATUS.has(record.status) &&
          record.reserve_date >= range.startDate &&
          record.reserve_date <= range.endDate,
      )

      for (const bucket of SLOT_BUCKETS) {
        let occupied = 0
        for (const record of records) {
          const recordStart = parseTimeMinutes(record.start_time) ?? 0
          const recordEnd = parseTimeMinutes(record.end_time) ?? 0
          const overlap = Math.min(recordEnd, bucket.end) - Math.max(recordStart, bucket.start)
          if (overlap > 0) occupied += overlap / SLOT_MINUTES
        }
        const capacity = seats.length * ((bucket.end - bucket.start) / SLOT_MINUTES) * days
        rows.push({
          room_id: room.id,
          room_name: room.name,
          slot: bucket.label,
          occupied,
          capacity,
          rate: capacity > 0 ? Math.round((occupied / capacity) * 10000) / 10000 : 0,
        })
    }
  }
  return rows
}

function trendOf(db: MockDb, range: Range): TrendPoint[] {
  const start = parseDate(range.startDate)
  const end = parseDate(range.endDate)
  if (!start || !end) return []
  const total = dayDiff(start, end)
  if (total < 0 || total > MAX_TREND_DAYS) return []

  const { reservations, violations } = scopeOf(db, range.roomId)
  const points: TrendPoint[] = []
  for (let offset = 0; offset <= total; offset += 1) {
    const date = formatDate(addDays(start, offset))
    points.push({
      date,
      reservations: reservations.filter(
        (record) => createdAtDay(record.created_at) === date && record.status !== '已取消',
      ).length,
      violations: violations.filter((record) => createdAtDay(record.created_at) === date).length,
    })
}
return points
}

type ParsedRange = { ok: true; range: Range } | { ok: false; message: string }

/** 解析查询参数；非法参数返回错误文案（前端据此验证失败态） */
function readRange(query: URLSearchParams): ParsedRange {
  const startDate = strParam(query, 'start_date')
  const endDate = strParam(query, 'end_date')
  const start = parseDate(startDate)
  const end = parseDate(endDate)
  if (!start || !end) {
    return { ok: false, message: 'start_date 与 end_date 必填且格式为 YYYY-MM-DD' }
  }
  if (dayDiff(start, end) < 0) return { ok: false, message: '结束日期不能早于开始日期' }

  const roomIdRaw = strParam(query, 'room_id')
  let roomId: number | null = null
  if (roomIdRaw !== '') {
    const parsed = Number(roomIdRaw)
    if (!Number.isInteger(parsed) || parsed <= 0) {
      return { ok: false, message: 'room_id 必须为正整数' }
    }
    roomId = parsed
  }
  return { ok: true, range: { startDate, endDate, roomId } }
}

function roomMissing(range: Range): boolean {
  if (range.roomId === null) return false
  return !getDb().rooms.some((room) => room.id === range.roomId)
}

function tooLong(range: Range): boolean {
  const start = parseDate(range.startDate)
  const end = parseDate(range.endDate)
  if (!start || !end) return false
  return dayDiff(start, end) > MAX_TREND_DAYS
}

export const dashboardHandlers = [
  http.get('/api/v1/dashboard/overview', ({ request }) =>
      safe(() => {
      requireAdmin(request)
      const parsed = readRange(new URL(request.url).searchParams)
      if (!parsed.ok) return abort(400, 'INVALID_ARGUMENT', parsed.message)
      if (roomMissing(parsed.range)) return abort(404, 'ROOM_NOT_FOUND', '自习室不存在')
      return json(overviewOf(getDb(), parsed.range.roomId))
    }),
),

http.get('/api/v1/dashboard/seat-usage', ({ request }) =>
    safe(() => {
    requireAdmin(request)
    const query = new URL(request.url).searchParams
    const parsed = readRange(query)
    if (!parsed.ok) return abort(400, 'INVALID_ARGUMENT', parsed.message)
    if (roomMissing(parsed.range)) return abort(404, 'ROOM_NOT_FOUND', '自习室不存在')
    if (tooLong(parsed.range)) {
      return abort(400, 'INVALID_ARGUMENT', `统计区间不能超过 ${MAX_TREND_DAYS} 天`)
      }
      if (strParam(query, 'group_by') === 'slot') {
        return json(slotOccupancyOf(getDb(), parsed.range))
      }
      return json(seatUsageOf(getDb(), parsed.range))
    }),
  ),

  http.get('/api/v1/dashboard/trend', ({ request }) =>
    safe(() => {
      requireAdmin(request)
      const parsed = readRange(new URL(request.url).searchParams)
      if (!parsed.ok) return abort(400, 'INVALID_ARGUMENT', parsed.message)
      if (roomMissing(parsed.range)) return abort(404, 'ROOM_NOT_FOUND', '自习室不存在')
      if (tooLong(parsed.range)) {
        return abort(400, 'INVALID_ARGUMENT', `统计区间不能超过 ${MAX_TREND_DAYS} 天`)
      }
      return json(trendOf(getDb(), parsed.range))
    }),
),
]
