/**
 * mock 层的业务规则判定（与需求规格说明书 BR-001～BR-021 对齐）。
 *
 * 纯函数为主：入参是内存库与用户，返回 Result；不直接返回 HTTP 响应，
 * 由 handlers 通过 responses.ts 的 fromError 转换，便于单独核对规则。
 */
import type { Reservation, Room, Seat } from '@/types'

import type { MockDb, ReservationRecord, UserRecord } from './db'
import {
  combine,
  dayDiff,
  formatDate,
  formatDateTime,
  minutesOfDay,
  overlaps,
  parseDate,
  parseTimeMinutes,
  readableDateTime,
  serverNow,
  startOfDay,
} from './time'

/** 与 backend/app/core/config.py 的业务参数保持一致。 */
export const RULES = {
  granularity: 30,
  advanceDays: 7,
  maxHours: 4,
  dailyLimit: 2,
  checkinEarly: 15,
  checkinLate: 15,
  cancelBefore: 30,
  violationThreshold: 3,
  restrictionDays: 7,
} as const

const EFFECTIVE_STATUS: readonly Reservation['status'][] = ['待使用', '使用中']

export function isEffective(status: Reservation['status']): boolean {
  return EFFECTIVE_STATUS.includes(status)
}

export interface RuleError {
  status: number
  code: string
  message: string
  extra?: Record<string, unknown>
}

export type Result<T> = { ok: true; value: T } | { ok: false; error: RuleError }

export function ok<T>(value: T): Result<T> {
  return { ok: true, value }
}

export function fail<T>(
  status: number,
  code: string,
  message: string,
  extra?: Record<string, unknown>,
): Result<T> {
  return { ok: false, error: { status, code, message, extra } }
}

export interface Slot {
  day: Date
  start: number
  end: number
}

export interface SlotInput {
  reserve_date: string
  start_time: string
  end_time: string
}

function openMinutes(room: Room): number {
  return parseTimeMinutes(room.open_time) ?? 8 * 60
}

function closeMinutes(room: Room): number {
  return parseTimeMinutes(room.close_time) ?? 22 * 60
}

function slotStart(record: Reservation): number {
  return parseTimeMinutes(record.start_time) ?? 0
}

function slotEnd(record: Reservation): number {
  return parseTimeMinutes(record.end_time) ?? 0
}

/** 形如 `14:00–16:00`，用于错误提示。 */
export function readableRange(record: Pick<Reservation, 'start_time' | 'end_time'>): string {
  return `${record.start_time.slice(0, 5)}–${record.end_time.slice(0, 5)}`
}

function overlapsSlot(record: Reservation, slot: Slot): boolean {
  return overlaps(slot.start, slot.end, slotStart(record), slotEnd(record))
}

function findSeatConflict(
  records: readonly ReservationRecord[],
  seatId: number,
  date: string,
  slot: Slot,
): ReservationRecord | undefined {
  return records.find(
    (item) =>
      item.seat_id === seatId &&
      item.reserve_date === date &&
      isEffective(item.status) &&
      overlapsSlot(item, slot),
  )
}

/**
 * 当前生效的**自动**限制截止时间（ISO 字符串），无自动限制返回 null。
 *
 * 手动限制不产生“自动解除时间”（BR-010 / ST-042），因此不在此处返回。
 */
export function restrictionUntil(db: MockDb, userId: number): string | null {
  const nowMs = serverNow().getTime()
  const active = db.blacklist.filter(
    (item) =>
      item.user_id === userId &&
      item.released_at === null &&
      item.mode === '自动' &&
      item.expire_at !== null &&
      new Date(item.expire_at).getTime() > nowMs,
  )
  if (active.length === 0) return null
  const expiries = active.map((item) => item.expire_at ?? '')
  return expiries.sort()[0] ?? null
}

/**
 * 是否存在生效中的限制（BR-010 / ST-042）。
 *
 * 与 `restrictionUntil` 的区别：管理员手动限制**无论是否设期限**都算生效中。
 * ST-042 要求「存在管理员手动限制时系统不得自动解除」，因此判断账户能否恢复
 * 「正常」时必须用它，而不能只看有没有到期时间。
 */
    export function hasActiveRestriction(db: MockDb, userId: number): boolean {
    const nowMs = serverNow().getTime()
    return db.blacklist.some(
      (item) =>
          item.user_id === userId &&
          item.released_at === null &&
          (item.mode === '手动' ||
              item.expire_at === null ||
              new Date(item.expire_at).getTime() > nowMs),
      )
    }

    /** 账户状态校验（BR-009 / BR-010）：受限账户返回预计解除时间。 */
    export function validateAccount(db: MockDb, user: UserRecord): Result<UserRecord> {
      if (user.account_status === '停用') {
        return fail(403, 'ACCOUNT_DISABLED', '账户已停用，请联系管理员')
      }
      if (user.account_status === '受限') {
        const until = restrictionUntil(db, user.id)
        if (until === null) {
          // 管理员手动限制没有自动解除时间；ST-042 要求必须由管理员解除
          return fail(
            403,
            'ACCOUNT_RESTRICTED',
            hasActiveRestriction(db, user.id)
              ? '账户当前处于受限状态（管理员手动限制），须由管理员解除后恢复，暂不可预约'
              : '账户当前处于受限状态，暂不可预约，请联系管理员',
          )
        }
        return fail(
          403,
          'ACCOUNT_RESTRICTED',
          `账户当前处于受限状态，预计 ${readableDateTime(until)} 解除限制，暂不可预约`,
      { rule: 'BR-009', restrict_until: until },
    )
  }
  return ok(user)
}

/** 解析并校验时段：粒度、时长上限、可预约日期范围（BR-001～BR-003）。 */
export function parseSlot(input: SlotInput): Result<Slot> {
  const day = parseDate(input.reserve_date)
  if (day === null) {
    return fail(400, 'INVALID_ARGUMENT', '预约日期格式应为 YYYY-MM-DD')
  }
  const start = parseTimeMinutes(input.start_time)
  const end = parseTimeMinutes(input.end_time)
  if (start === null || end === null) {
    return fail(400, 'INVALID_ARGUMENT', '时间格式应为 HH:MM 或 HH:MM:SS')
  }
  if (start >= end) {
    return fail(400, 'INVALID_ARGUMENT', '结束时间必须晚于开始时间', { rule: 'BR-020' })
  }
  if (start % RULES.granularity !== 0 || end % RULES.granularity !== 0) {
    return fail(
      400,
      'TIME_NOT_ALIGNED',
      `预约时间须以 ${RULES.granularity} 分钟为粒度，开始与结束时间必须对齐整点或半点`,
          { rule: 'BR-001' },
        )
      }
      if (end - start > RULES.maxHours * 60) {
        return fail(400, 'DURATION_EXCEEDED', `单次预约时长不能超过 ${RULES.maxHours} 小时`, {
      rule: 'BR-003',
    })
  }
  const offset = dayDiff(startOfDay(serverNow()), day)
  if (offset < 0) {
    return fail(400, 'DATE_OUT_OF_RANGE', '不能预约已经过去的日期', { rule: 'BR-002' })
  }
  if (offset > RULES.advanceDays) {
    return fail(400, 'DATE_OUT_OF_RANGE', `最多只能提前 ${RULES.advanceDays} 天预约`, {
          rule: 'BR-002',
        })
    }
    return ok({ day, start, end })
  }

  function validateNotStarted(slot: Slot): Result<Slot> {
    const now = serverNow()
    if (dayDiff(startOfDay(now), slot.day) === 0 && slot.start <= minutesOfDay(now)) {
      return fail(400, 'TIME_STARTED', '该时段已经开始，不能预约')
    }
    return ok(slot)
  }

  export interface BookingInput extends SlotInput {
    seat_id: number
  }

  export interface BookingPlan {
    seat: Seat
    room: Room
    slot: Slot
  }

  /**
   * 创建预约的完整判定：C1 座位可用、C2 开放时间、C3 座位冲突、
   * C4 本人时段不重叠、C5 账户状态、C6 粒度/天数/时长/每日次数。
   */
  export function validateBooking(
    db: MockDb,
    user: UserRecord,
    input: BookingInput,
  ): Result<BookingPlan> {
    if (!Number.isInteger(input.seat_id)) {
      return fail(400, 'INVALID_ARGUMENT', '座位参数不合法')
    }
    const slotResult = parseSlot(input)
    if (!slotResult.ok) return slotResult
    const slot = slotResult.value

    const notStarted = validateNotStarted(slot)
    if (!notStarted.ok) return notStarted

    const account = validateAccount(db, user)
    if (!account.ok) return account

    const seat = db.seats.find((item) => item.id === input.seat_id)
    if (!seat) return fail(404, 'SEAT_NOT_FOUND', '座位不存在')
    const room = db.rooms.find((item) => item.id === seat.room_id)
    if (!room || !room.enabled) {
      return fail(400, 'ROOM_UNAVAILABLE', '该自习室当前不可用')
    }
    if (slot.start < openMinutes(room) || slot.end > closeMinutes(room)) {
      return fail(400, 'OUT_OF_OPEN_HOURS', `超出自习室开放时间（${room.open_time}–${room.close_time}）`, {
      rule: 'BR-002',
    })
  }
  if (seat.status !== '可用') {
    return fail(400, 'SEAT_UNAVAILABLE', `座位 ${seat.seat_no} 当前状态为「${seat.status}」，不可预约`, {
        rule: 'BR-017',
      })
  }

  const date = formatDate(slot.day)
  const dailyCount = db.reservations.filter(
    (item) =>
        item.user_id === user.id && item.reserve_date === date && isEffective(item.status),
    ).length
    if (dailyCount >= RULES.dailyLimit) {
      return fail(
        400,
        'DAILY_LIMIT',
        `每位用户每日最多 ${RULES.dailyLimit} 条有效预约，你当日已有 ${dailyCount} 条`,
      { rule: 'BR-004' },
    )
  }

  const seatConflict = findSeatConflict(db.reservations, seat.id, date, slot)
  if (seatConflict) {
    return fail(
      400,
      'SEAT_CONFLICT',
      `座位 ${seat.seat_no} 在 ${readableRange(seatConflict)} 已被预约，请改选其他时段`,
        { rule: 'BR-006' },
      )
    }

    const userConflict = db.reservations.find(
      (item) =>
          item.user_id === user.id &&
          item.reserve_date === date &&
          isEffective(item.status) &&
          overlapsSlot(item, slot),
      )
      if (userConflict) {
        return fail(400, 'USER_CONFLICT', `你在 ${readableRange(userConflict)} 已有有效预约，该时段不能重复预约`, {
      rule: 'BR-005',
    })
  }

  return ok({ seat, room, slot })
}

export interface SeatQueryInput extends SlotInput {
  room_id: number
}

export interface SeatQueryPlan {
  room: Room
  slot: Slot
}

/** 可预约座位查询的前置校验（C2 / C5 / C6），座位级过滤见 availableSeats。 */
export function validateSeatQuery(
  db: MockDb,
  user: UserRecord,
  input: SeatQueryInput,
): Result<SeatQueryPlan> {
  if (!Number.isInteger(input.room_id)) {
    return fail(400, 'INVALID_ARGUMENT', '自习室参数不合法')
  }
  const slotResult = parseSlot(input)
  if (!slotResult.ok) return slotResult
  const slot = slotResult.value
  const notStarted = validateNotStarted(slot)
  if (!notStarted.ok) return notStarted
  const account = validateAccount(db, user)
  if (!account.ok) return account
  const room = db.rooms.find((item) => item.id === input.room_id)
  if (!room || !room.enabled) {
    return fail(400, 'ROOM_UNAVAILABLE', '该自习室当前不可用')
  }
  if (slot.start < openMinutes(room) || slot.end > closeMinutes(room)) {
    return fail(400, 'OUT_OF_OPEN_HOURS', `超出自习室开放时间（${room.open_time}–${room.close_time}）`)
        }
        return ok({ room, slot })
      }

      /**
       * C1（资源状态为可用）+ C3（无重叠有效预约）过滤座位。
       * C4（本人无重叠有效预约）或 C6（当日次数已达上限）时，该时段对本用户没有可选座位。
       */
      export function availableSeats(db: MockDb, user: UserRecord, plan: SeatQueryPlan): Seat[] {
        const date = formatDate(plan.slot.day)
        const userBusy = db.reservations.some(
          (item) =>
              item.user_id === user.id &&
              item.reserve_date === date &&
              isEffective(item.status) &&
              overlapsSlot(item, plan.slot),
          )
          if (userBusy) return []
          const dailyCount = db.reservations.filter(
            (item) => item.user_id === user.id && item.reserve_date === date && isEffective(item.status),
          ).length
          if (dailyCount >= RULES.dailyLimit) return []
          return db.seats.filter(
            (seat) =>
                seat.room_id === plan.room.id &&
                seat.status === '可用' &&
                !findSeatConflict(db.reservations, seat.id, date, plan.slot),
            )
          }

          export interface CheckInPlan {
            record: ReservationRecord
            repeat: boolean
          }

          /** 签到窗口 [s-15min, s+15min)（BR-007），重复签到幂等（FR-015）。 */
          export function validateCheckIn(
            db: MockDb,
            user: UserRecord,
            reservationId: number,
          ): Result<CheckInPlan> {
            const record = db.reservations.find((item) => item.id === reservationId)
            if (!record) return fail(404, 'RESERVATION_NOT_FOUND', '预约单不存在')
            if (record.user_id !== user.id) {
              return fail(403, 'RESERVATION_NOT_OWNED', '只能操作本人的预约单')
            }
            if (record.status === '使用中') return ok({ record, repeat: true })
            if (record.status !== '待使用') {
              return fail(400, 'STATUS_NOT_ALLOWED', `当前状态为「${record.status}」，不能签到`)
  }
  const day = parseDate(record.reserve_date) ?? startOfDay(serverNow())
  const startAt = combine(day, slotStart(record)).getTime()
  const opensAt = new Date(startAt - RULES.checkinEarly * 60_000)
  const closesAt = new Date(startAt + RULES.checkinLate * 60_000)
  const now = serverNow()
  if (now.getTime() < opensAt.getTime()) {
    return fail(
      400,
      'CHECKIN_NOT_OPEN',
      `签到窗口尚未开启：${readableDateTime(formatDateTime(opensAt))} 起可签到（开始前 ${RULES.checkinEarly} 分钟）`,
                { rule: 'BR-007', window_opens_at: formatDateTime(opensAt) },
              )
            }
            if (now.getTime() >= closesAt.getTime()) {
              return fail(
                400,
                'CHECKIN_EXPIRED',
                `已超过签到截止时间 ${readableDateTime(formatDateTime(closesAt))}（开始后 ${RULES.checkinLate} 分钟），该预约将判定为违约`,
      { rule: 'BR-007', window_closed_at: formatDateTime(closesAt) },
    )
  }
  return ok({ record, repeat: false })
}

export function validateCheckOut(
  db: MockDb,
  user: UserRecord,
  reservationId: number,
): Result<ReservationRecord> {
  const record = db.reservations.find((item) => item.id === reservationId)
  if (!record) return fail(404, 'RESERVATION_NOT_FOUND', '预约单不存在')
  if (record.user_id !== user.id) {
    return fail(403, 'RESERVATION_NOT_OWNED', '只能操作本人的预约单')
  }
  if (record.status !== '使用中') {
    return fail(400, 'STATUS_NOT_ALLOWED', `仅「使用中」的预约可签退（当前状态：${record.status}）`)
              }
              return ok(record)
            }

            /** 用户自行取消：仅「待使用」且距开始 ≥ 30 分钟（BR-011）。 */
            export function validateCancel(
              record: ReservationRecord,
              user: UserRecord,
            ): Result<ReservationRecord> {
              if (record.user_id !== user.id) {
                return fail(403, 'RESERVATION_NOT_OWNED', '只能操作本人的预约单')
              }
              if (record.status !== '待使用') {
                return fail(400, 'STATUS_NOT_ALLOWED', `当前状态为「${record.status}」，不能取消`)
  }
  const day = parseDate(record.reserve_date) ?? startOfDay(serverNow())
  const deadline = combine(day, slotStart(record)).getTime() - RULES.cancelBefore * 60_000
  if (serverNow().getTime() > deadline) {
    return fail(
      400,
      'CANCEL_TOO_LATE',
      `距预约开始不足 ${RULES.cancelBefore} 分钟，不能自行取消（该情形不计违约）`,
                  { rule: 'BR-011' },
                )
              }
              return ok(record)
            }

            /** 管理员强制取消：仅「待使用」，与手动违约互斥（BR-015）。 */
            export function validateForceCancel(record: ReservationRecord): Result<ReservationRecord> {
              if (record.status !== '待使用') {
                return fail(
                  400,
                  'STATUS_NOT_ALLOWED',
                  `仅「待使用」的预约可强制取消（当前状态：${record.status}）`,
      { rule: 'BR-015' },
    )
  }
  return ok(record)
}

/** 手动违约登记：仅「使用中」，与强制取消互斥（BR-015）。 */
export function validateManualViolation(record: ReservationRecord): Result<ReservationRecord> {
  if (record.status !== '使用中') {
    return fail(
      400,
      'STATUS_NOT_ALLOWED',
      `仅「使用中」的预约可登记手动违约（当前状态：${record.status}）`,
                  { rule: 'BR-015' },
                )
              }
              return ok(record)
            }

            /** 评价资格：本人「已完成」预约，一单一评（BR-013）。 */
            export function validateReview(
              db: MockDb,
              user: UserRecord,
              reservationId: number,
            ): Result<ReservationRecord> {
              const record = db.reservations.find((item) => item.id === reservationId)
              if (!record) return fail(404, 'RESERVATION_NOT_FOUND', '预约单不存在')
              if (record.user_id !== user.id) {
                return fail(403, 'RESERVATION_NOT_OWNED', '只能评价本人的预约单')
              }
              if (record.status !== '已完成') {
                return fail(400, 'STATUS_NOT_ALLOWED', `仅「已完成」的预约可评价（当前状态：${record.status}）`, {
      rule: 'BR-013',
    })
  }
  if (db.reviews.some((item) => item.reservation_id === reservationId)) {
    return fail(400, 'REVIEW_EXISTS', '该预约已评价，不能重复评价', { rule: 'BR-013' })
  }
  return ok(record)
}
