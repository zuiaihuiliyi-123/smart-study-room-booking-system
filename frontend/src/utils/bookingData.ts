/**
 * 预约座位页与首页共用的取数辅助：座位目录、本人预约全量、时段可用性聚合。
 *
 * 两个已知的接口限制（均登记在每轮交付说明的「问题清单」中）：
 * 1. `ReservationRead` 只有 `seat_id`，没有 `seat_no` / 自习室名。要显示「第一自习室 · A-01」
 *    只能先取 `/rooms` 再逐个取 `/rooms/{id}/seats` 建一份本地目录（本文件首屏缓存一次）。
 * 2. 后端没有 `GET /rooms/{room_id}/areas`（只有 POST 建区域），因此分区名称不可得：
 *    矩阵按 `area_id` 分组，组标题用座位号前缀推断（推断不出时退回 `分区 #id`）。
 */
import { isAxiosError } from 'axios'

import { listAvailableSeats, listMyReservations } from '@/api/reservation'
import { listRooms } from '@/api/room'
import { listSeats } from '@/api/seat'
import type { Reservation, Room, Seat } from '@/types'
import {
  ceilToStep,
  mapBookingFailure,
  minutesToTimeText,
  parseTimeToMinutes,
  type BookingFailure,
} from '@/utils/bookingRules'

/* ------------------------------------------------------------------ 座位目录 */

export interface SeatRef {
  seatId: number
  seatNo: string
  roomId: number
  roomName: string
  areaId: number | null
}

let directoryPromise: Promise<Map<number, SeatRef>> | null = null

function buildDirectory(): Promise<Map<number, SeatRef>> {
  return listRooms().then((rooms) =>
      Promise.all(rooms.map(async (room) => ({ room, seats: await listSeats(room.id) }))).then(
      (groups) => {
        const map = new Map<number, SeatRef>()
        for (const group of groups) {
          for (const seat of group.seats) {
            map.set(seat.id, {
              seatId: seat.id,
              seatNo: seat.seat_no,
              roomId: group.room.id,
              roomName: group.room.name,
              areaId: seat.area_id,
            })
        }
      }
      return map
    },
  ),
)
}

/** 首屏缓存一次的「座位 id → 座位号 + 自习室名」目录；失败时清空缓存以便重试。 */
export function loadSeatDirectory(force = false): Promise<Map<number, SeatRef>> {
  if (force) directoryPromise = null
  if (directoryPromise === null) {
    directoryPromise = buildDirectory().catch((error: unknown) => {
      directoryPromise = null
      throw error
    })
}
return directoryPromise
}

export function invalidateSeatDirectory(): void {
  directoryPromise = null
}

export function seatDisplayName(
  directory: Map<number, SeatRef> | null,
  seatId: number,
): string {
  const ref = directory?.get(seatId)
  return ref ? `${ref.roomName} · ${ref.seatNo}` : `座位 #${seatId}`
}

/* ------------------------------------------------------------------ 本人预约 */

/**
 * 取本人全部预约（`/reservations/me` 无日期过滤、`page_size` 上限 100）。
 * 首页与预约页都需要按日期筛选当日记录，分页截断会让「今日预约」漏数据，故此处翻页取全量。
 */
export async function fetchAllMyReservations(pageSize = 100, maxPages = 10): Promise<Reservation[]> {
  const collected: Reservation[] = []
  for (let page = 1; page <= maxPages; page += 1) {
    const result = await listMyReservations({ page, page_size: pageSize })
    collected.push(...result.items)
    if (result.items.length === 0 || collected.length >= result.total) break
  }
  return collected
}

/* ------------------------------------------------------------------ 时段可用性 */

export interface SlotAvailability {
  /** 该自习室全部座位（含维修中 / 停用）——资源状态一列 */
  seats: Seat[]
  /** 该时段的可预约座位 id 集合——时段占用一列（C1 + C3 过滤后的结果） */
  availableIds: Set<number>
  /** 本人全部预约，用于 C4 / C6 与首页「今日预约」 */
  myReservations: Reservation[]
}

export async function loadSlotAvailability(
  roomId: number,
  reserveDate: string,
  startTime: string,
  endTime: string,
): Promise<SlotAvailability> {
  const [seats, available, myReservations] = await Promise.all([
    listSeats(roomId),
    listAvailableSeats({
      room_id: roomId,
      reserve_date: reserveDate,
      start_time: startTime,
      end_time: endTime,
    }),
  fetchAllMyReservations(),
])
return {
  seats,
  availableIds: new Set(available.map((seat) => seat.id)),
  myReservations,
}
}

/* ------------------------------------------------------------------ 分区分组 */

export interface SeatGroupData {
  key: string
  title: string
  note: string
  seats: Seat[]
}

function areaPrefix(seats: readonly Seat[]): string {
  const prefixes = new Set(
    seats.map((seat) => seat.seat_no.split('-')[0]?.trim().toUpperCase() ?? ''),
  )
  if (prefixes.size !== 1) return ''
  const [prefix] = [...prefixes]
  return /^[A-Z]{1,3}$/.test(prefix) ? prefix : ''
}

/** 按 `area_id` 分组；组标题优先用座位号前缀推断，推断不出时退回 `分区 #id`。 */
export function groupSeatsByArea(seats: readonly Seat[]): SeatGroupData[] {
  const groups: SeatGroupData[] = []
  for (const seat of seats) {
    const key = seat.area_id === null ? 'unassigned' : String(seat.area_id)
    let group = groups.find((item) => item.key === key)
    if (!group) {
      group = { key, title: '', note: '', seats: [] }
      groups.push(group)
    }
    group.seats.push(seat)
  }
  return groups.map((group) => {
    const prefix = areaPrefix(group.seats)
    const types = [...new Set(group.seats.map((seat) => seat.seat_type))]
    return {
        ...group,
      title:
      group.key === 'unassigned'
        ? '未分区'
        : prefix
        ? `分区 ${prefix}`
        : `分区 #${group.key}`,
      note: `共 ${group.seats.length} 座 · ${types.join(' / ')}`,
    }
  })
}

/**
 * 默认时段：从「当前时刻向上对齐粒度」开始，取 2 小时；越过闭馆则前移。
 * 仅用于表单初值，仍以服务端判定为准。
 */
export function defaultBookingSlot(
  room: Room | null,
  now: Date,
): { startTime: string; endTime: string } {
  const open = parseTimeToMinutes(room?.open_time) ?? 8 * 60
  const close = parseTimeToMinutes(room?.close_time) ?? 22 * 60
  const nowMinutes = now.getHours() * 60 + now.getMinutes()
  const aligned = ceilToStep(Math.max(open, nowMinutes))
  const start = Math.min(Math.max(aligned, open), Math.max(open, close - 60))
  const end = Math.min(start + 120, close)
  return { startTime: minutesToTimeText(start), endTime: minutesToTimeText(end) }
}

/** 指定日期的默认时段：今天沿用「当前时刻对齐」，其它日期从开放时间起取 2 小时。 */
export function defaultSlotForDate(
  room: Room | null,
  dateIso: string,
  now: Date,
): { startTime: string; endTime: string } {
  const today = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(
      now.getDate(),
    ).padStart(2, '0')}`
    if (dateIso === today) return defaultBookingSlot(room, now)
    const open = parseTimeToMinutes(room?.open_time) ?? 8 * 60
    const close = parseTimeToMinutes(room?.close_time) ?? 22 * 60
    return {
      startTime: minutesToTimeText(open),
      endTime: minutesToTimeText(Math.min(open + 120, close)),
    }
  }

  /** 把 axios / 未知异常统一转成界面可渲染的失败描述（文案取服务端返回）。 */
  export function toBookingFailure(error: unknown): BookingFailure {
    if (isAxiosError(error)) {
      return mapBookingFailure(error.response?.status, error.response?.data)
    }
    return mapBookingFailure(undefined, undefined)
  }
