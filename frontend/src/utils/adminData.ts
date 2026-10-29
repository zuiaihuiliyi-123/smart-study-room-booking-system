/**
 * 管理端共用的「业务对象目录」：把 id 翻译成人能读的一行，并在各页面间复用同一份缓存。
 *
 * 为什么需要它（均为接口现状造成的、已登记在问题清单中的限制）：
 * 1. `ReservationRead` 只有 `seat_id`，没有座位号与自习室名 —— 要显示「第一自习室 · A-01」
 *    必须自行拼装座位目录（与学生端 `bookingData.ts` 的做法一致）。
 * 2. 后端**没有** `GET /rooms/{room_id}/areas`（只有 POST 建区域）—— 分区名称可能取不到，
 *    此时按座位号前缀推断并明确标注「分区名称待后端提供接口」，不编造名称。
 * 3. 列表接口都只按 id 关联用户 —— 学号 / 姓名需要 `GET /users` 目录（管理员可读）。
 *
 * 所有写操作完成后调用 `invalidateAdminDirectory()`，避免页面之间读到过期对象。
 */
import { listAllReservations } from '@/api/reservation'
import { listAreas, listRooms } from '@/api/room'
import { listSeats } from '@/api/seat'
import { listUsers } from '@/api/user'
import type { Area, CurrentUser, Reservation, Room, Seat } from '@/types'
import { bracketRangeText, isEffectiveReservation } from '@/utils/bookingRules'

export interface AdminDirectory {
  rooms: Room[]
  areas: Area[]
  seats: Seat[]
  users: CurrentUser[]
  reservations: Reservation[]
  roomsById: Map<number, Room>
  areasById: Map<number, Area>
  seatsById: Map<number, Seat>
  usersById: Map<number, CurrentUser>
  usersByStudentNo: Map<string, CurrentUser>
  reservationsById: Map<number, Reservation>
  seatsByRoom: Map<number, Seat[]>
  areasByRoom: Map<number, Area[]>
  /** `GET /rooms/{id}/areas` 是否可用（后端缺失时为 false，界面据此标注） */
  areasAvailable: boolean
}

let cache: AdminDirectory | null = null
let pending: Promise<AdminDirectory> | null = null

async function fetchAllUsers(): Promise<CurrentUser[]> {
  const collected: CurrentUser[] = []
  for (let page = 1; page <= 5; page += 1) {
    const result = await listUsers({ page, page_size: 100 })
    collected.push(...result.items)
    if (result.items.length === 0 || collected.length >= result.total) break
  }
  return collected
}

async function fetchAllReservations(): Promise<Reservation[]> {
  const collected: Reservation[] = []
  for (let page = 1; page <= 5; page += 1) {
    const result = await listAllReservations({ page, page_size: 100 })
    collected.push(...result.items)
    if (result.items.length === 0 || collected.length >= result.total) break
  }
  return collected
}

function indexBy<T, K>(items: readonly T[], keyOf: (item: T) => K): Map<K, T> {
  const map = new Map<K, T>()
  for (const item of items) map.set(keyOf(item), item)
  return map
}

function groupBy<T, K>(items: readonly T[], keyOf: (item: T) => K): Map<K, T[]> {
  const map = new Map<K, T[]>()
  for (const item of items) {
    const key = keyOf(item)
    const bucket = map.get(key)
    if (bucket) bucket.push(item)
    else map.set(key, [item])
  }
  return map
}

async function build(): Promise<AdminDirectory> {
  const [rooms, users, reservations] = await Promise.all([
    listRooms(),
    fetchAllUsers().catch(() => [] as CurrentUser[]),
    fetchAllReservations().catch(() => [] as Reservation[]),
  ])

let areasAvailable = true
const groups = await Promise.all(
  rooms.map(async (room) => {
    const [seats, areas] = await Promise.all([
      listSeats(room.id).catch(() => [] as Seat[]),
      listAreas(room.id).catch(() => {
        areasAvailable = false
        return [] as Area[]
      }),
  ])
return { room, seats, areas }
}),
)

const seats = groups.flatMap((group) => group.seats)
const areas = groups.flatMap((group) => group.areas)

return {
  rooms,
  areas,
  seats,
  users,
  reservations,
  roomsById: indexBy(rooms, (item) => item.id),
  areasById: indexBy(areas, (item) => item.id),
  seatsById: indexBy(seats, (item) => item.id),
  usersById: indexBy(users, (item) => item.id),
  usersByStudentNo: indexBy(users, (item) => item.student_no),
  reservationsById: indexBy(reservations, (item) => item.id),
  seatsByRoom: groupBy(seats, (item) => item.room_id),
  areasByRoom: groupBy(areas, (item) => item.room_id),
  areasAvailable,
}
}

/** 首屏缓存一次的目录；失败会清空缓存以便重试。 */
export function loadAdminDirectory(force = false): Promise<AdminDirectory> {
  if (force) {
    cache = null
    pending = null
  }
  if (cache !== null) return Promise.resolve(cache)
  if (pending === null) {
    pending = build()
      .then((directory) => {
      cache = directory
      return directory
    })
    .finally(() => {
    pending = null
  })
}
return pending
}

export function invalidateAdminDirectory(): void {
  cache = null
  pending = null
}

/* ------------------------------------------------------------------ 标签 */

export function roomNameOf(directory: AdminDirectory | null, roomId: number): string {
  return directory?.roomsById.get(roomId)?.name ?? `自习室 #${roomId}`
}

/** 分区名称：优先用接口返回的名称，缺失时按座位号前缀推断，再不行退回 `分区 #id`。 */
export function areaLabelOf(
  directory: AdminDirectory | null,
  areaId: number | null,
  seats: readonly Seat[] = [],
): string {
  if (areaId === null) return '未分区'
  const named = directory?.areasById.get(areaId)?.name
  if (named) return named
  const scoped = seats.filter((seat) => seat.area_id === areaId)
  const prefixes = new Set(
    scoped.map((seat) => seat.seat_no.split('-')[0]?.trim().toUpperCase() ?? ''),
  )
  if (prefixes.size === 1) {
    const [prefix] = [...prefixes]
    if (/^[A-Z]{1,3}$/.test(prefix)) return `分区 ${prefix}（名称待后端提供接口）`
  }
  return `分区 #${areaId}（名称待后端提供接口）`
}

export function seatLabelOf(directory: AdminDirectory | null, seat: Seat | null): string {
  if (!seat) return '—'
  return `${roomNameOf(directory, seat.room_id)} · ${seat.seat_no}`
}

export function seatIdLabel(directory: AdminDirectory | null, seatId: number): string {
  return seatLabelOf(directory, directory?.seatsById.get(seatId) ?? null)
}

export function userLabelOf(directory: AdminDirectory | null, userId: number): string {
  const user = directory?.usersById.get(userId)
  return user ? `${user.name}（${user.student_no}）` : `用户 #${userId}`
}

export function studentNoOf(directory: AdminDirectory | null, userId: number): string {
  return directory?.usersById.get(userId)?.student_no ?? `#${userId}`
}

export function operatorLabelOf(directory: AdminDirectory | null, operatorId: number | null): string {
  if (operatorId === null) return '系统自动判定'
  const user = directory?.usersById.get(operatorId)
  return user ? `${user.name}（管理员 #${user.id}）` : `管理员 #${operatorId}`
}

export function reservationLabelOf(
  directory: AdminDirectory | null,
  reservationId: number,
): string {
  const record = directory?.reservationsById.get(reservationId)
  if (!record) return `预约单 #${reservationId}`
  return `#${record.id} · ${record.reserve_date} ${bracketRangeText(record.start_time, record.end_time)} · ${seatIdLabel(directory, record.seat_id)}`
}

/** 投诉对象的可读文案（FR-042 的 4 类对象）。 */
export function complaintTargetLabel(
  directory: AdminDirectory | null,
  targetType: string,
  targetId: number,
): string {
  if (targetType === '座位') return `座位 ${seatIdLabel(directory, targetId)}`
  if (targetType === '自习室') return `自习室 ${roomNameOf(directory, targetId)}`
  if (targetType === '预约单') return `预约单 ${reservationLabelOf(directory, targetId)}`
  if (targetType === '用户') return `用户 ${userLabelOf(directory, targetId)}`
  return `${targetType} #${targetId}`
}

/* ------------------------------------------------------------------ 统计 */

export function seatCountOfRoom(directory: AdminDirectory | null, roomId: number): number {
  return directory?.seatsByRoom.get(roomId)?.length ?? 0
}

export function areaCountOfRoom(directory: AdminDirectory | null, roomId: number): number {
  const named = directory?.areasByRoom.get(roomId)?.length ?? 0
  if (named > 0) return named
  const seats = directory?.seatsByRoom.get(roomId) ?? []
  return new Set(seats.map((seat) => seat.area_id).filter((id) => id !== null)).size
}

/** 某座位集合在窗口内的有效预约（待使用 / 使用中），用于 BR-019 冲突清单。 */
export function effectiveReservationsOf(
  reservations: readonly Reservation[],
  seatIds: readonly number[],
  fromMs: number,
  toMs: number,
): Reservation[] {
  const scope = new Set(seatIds)
  return reservations.filter((item) => {
    if (!scope.has(item.seat_id) || !isEffectiveReservation(item)) return false
    const start = new Date(`${item.reserve_date}T${item.start_time}`).getTime()
    const end = new Date(`${item.reserve_date}T${item.end_time}`).getTime()
    return start < toMs && fromMs < end
  })
}
