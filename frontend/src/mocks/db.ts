/**
 * mock 层的内存数据库：类型定义、状态容器、查询与写入辅助函数。
 *
 * 只存在于开发期；页面刷新后回到种子状态（reset 见 browser.ts 的 __ssrMock）。
 */
import type {
  Area,
  BlacklistEntry,
  Complaint,
  CurrentUser,
  PageResult,
  Reservation,
  Review,
  Room,
  Seat,
  StationMessage,
  Violation,
} from '@/types'

import { RULES } from './rules'
import { buildSeed } from './seed'
import { formatDateTime, serverNow } from './time'

/** 用户记录：比响应体多出口令，口令永远不会进入任何响应。 */
export interface UserRecord extends CurrentUser {
  password: string
  created_at: string
}

/** 预约记录：比响应体多出幂等键与更新时间（仅内部使用）。 */
export interface ReservationRecord extends Reservation {
  idempotency_key: string
  updated_at: string
}

/** 站内消息记录：响应体（MessageRead）不含 user_id，归属关系只存在于 mock 内部。 */
export interface MessageRecord extends StationMessage {
  user_id: number
}

export interface SessionRecord {
  user_id: number
  expires_at: number
}

/** 最近一次成功创建预约的「用户 + 座位 + 时段」，用于模拟并发冲突（NFR-003）。 */
export interface RaceAttempt {
  user_id: number
  seat_id: number
  reserve_date: string
  start: number
  end: number
  at: number
}

export interface MockDb {
  users: UserRecord[]
  rooms: Room[]
  areas: Area[]
  seats: Seat[]
  reservations: ReservationRecord[]
  violations: Violation[]
  reviews: Review[]
  complaints: Complaint[]
  blacklist: BlacklistEntry[]
  messages: MessageRecord[]
  sessions: Map<string, SessionRecord>
  attempts: RaceAttempt[]
  armed_conflicts: number
}

/** 并发冲突演示窗口：同一座位同一时段在此毫秒内再次提交视为“抢座”。 */
export const RACE_WINDOW_MS = 5_000

/** 登录态有效期，与后端 access_token_expire_minutes 一致。 */
const TOKEN_TTL_MS = 120 * 60_000

let state: MockDb | null = null

export function getDb(): MockDb {
  if (state === null) state = buildSeed()
  return state
}

export function resetDb(): MockDb {
  state = buildSeed()
  return state
}

export function nextId(items: readonly { id: number }[]): number {
  return items.reduce((max, item) => Math.max(max, item.id), 0) + 1
}

export function paginate<T>(items: readonly T[], page: number, pageSize: number): PageResult<T> {
  const safePage = Number.isFinite(page) ? Math.max(1, Math.trunc(page)) : 1
  const safeSize = Number.isFinite(pageSize)
    ? Math.min(100, Math.max(1, Math.trunc(pageSize)))
    : 20
  const offset = (safePage - 1) * safeSize
  return {
    items: items.slice(offset, offset + safeSize),
    total: items.length,
    page: safePage,
    page_size: safeSize,
  }
}

export function publicUser(user: UserRecord): CurrentUser {
  return {
    id: user.id,
    name: user.name,
    student_no: user.student_no,
    role: user.role,
    account_status: user.account_status,
    violation_count: user.violation_count,
    contact: user.contact,
  }
}

export function publicReservation(record: ReservationRecord): Reservation {
  return {
    id: record.id,
    user_id: record.user_id,
    seat_id: record.seat_id,
    reserve_date: record.reserve_date,
    start_time: record.start_time,
    end_time: record.end_time,
    status: record.status,
    check_in_time: record.check_in_time,
    check_out_time: record.check_out_time,
    cancel_time: record.cancel_time,
    cancel_reason: record.cancel_reason,
    created_at: record.created_at,
  }
}

export function publicMessage(record: MessageRecord): StationMessage {
  return {
    id: record.id,
    type: record.type,
    title: record.title,
    content: record.content,
    related_type: record.related_type,
    related_id: record.related_id,
    is_read: record.is_read,
    created_at: record.created_at,
  }
}

export function findUser(id: number): UserRecord | undefined {
  return getDb().users.find((item) => item.id === id)
}

export function findUserByStudentNo(studentNo: string): UserRecord | undefined {
  return getDb().users.find((item) => item.student_no === studentNo)
}

export function findSeat(id: number): Seat | undefined {
  return getDb().seats.find((item) => item.id === id)
}

export function findRoom(id: number): Room | undefined {
  return getDb().rooms.find((item) => item.id === id)
}

export function findReservation(id: number): ReservationRecord | undefined {
  return getDb().reservations.find((item) => item.id === id)
}

/** 座位展示名：`第一自习室 · A-01`，看板与列表共用。 */
export function seatLabel(seatId: number): string {
  const seat = findSeat(seatId)
  if (!seat) return `#${seatId}`
  const room = findRoom(seat.room_id)
  return room ? `${room.name} · ${seat.seat_no}` : seat.seat_no
}

export function createSession(userId: number): string {
  const token = `mock.${userId}.${Math.random().toString(36).slice(2, 12)}`
  getDb().sessions.set(token, { user_id: userId, expires_at: Date.now() + TOKEN_TTL_MS })
  return token
}

/**
 * 开发期便利：刷新页面会重建内存库（会话表随之清空），此时按 token 里的 userId 恢复会话，
 * 避免「按 F5 就被踢回登录页」。真后端没有这个行为（token 是不透明串），
 * 因此形如 `mock.<userId>.<random>` 之外的 token 依旧返回 401。
   */
    function restoreSession(token: string): SessionRecord | undefined {
    const matched = /^mock\.(\d+)\.[a-z0-9]+$/.exec(token)
    if (!matched) return undefined
    const userId = Number(matched[1])
    const user = getDb().users.find((item) => item.id === userId)
    if (!user || user.account_status === '停用') return undefined
    const session: SessionRecord = { user_id: userId, expires_at: Date.now() + TOKEN_TTL_MS }
    getDb().sessions.set(token, session)
    return session
  }

  export function resolveSession(token: string): SessionRecord | undefined {
    const session = getDb().sessions.get(token)
    if (!session) return restoreSession(token)
    if (session.expires_at <= Date.now()) {
      getDb().sessions.delete(token)
      return undefined
    }
    return session
  }

  /** 记录一次成功创建，用于识别 5 秒内的重复提交。 */
  export function noteAttempt(
    userId: number,
    seatId: number,
    reserveDate: string,
    start: number,
    end: number,
  ): void {
    const db = getDb()
    const now = Date.now()
    db.attempts = db.attempts.filter((item) => now - item.at < RACE_WINDOW_MS)
    db.attempts.push({ user_id: userId, seat_id: seatId, reserve_date: reserveDate, start, end, at: now })
  }

  /**
   * 判断本次提交是否应按「并发冲突」拒绝。
   * 优先级：显式布防（__ssrMock.armConflict）→ 5 秒内同一用户对同一座位同一时段的**完全重复提交**。
   *
   * 只认「完全一致」的时段：这样双指连点 / 双击才会得到 409，
   * 而“换个时段再试一次”仍然走正常规则校验（座位已占 → 400），不会把规则错误伪装成竞态。
   */
  export function consumeConflict(
    userId: number,
    seatId: number,
    reserveDate: string,
    start: number,
    end: number,
  ): boolean {
    const db = getDb()
    if (db.armed_conflicts > 0) {
      db.armed_conflicts -= 1
      return true
    }
    const now = Date.now()
    return db.attempts.some(
      (item) =>
          item.user_id === userId &&
          item.seat_id === seatId &&
          item.reserve_date === reserveDate &&
          item.start === start &&
          item.end === end &&
          now - item.at < RACE_WINDOW_MS,
      )
    }

    export function armConflict(times = 1): number {
      const db = getDb()
      db.armed_conflicts = Math.max(0, Math.trunc(times))
      return db.armed_conflicts
    }

    export function pushMessage(
      userId: number,
      input: {
        type: string
        title: string
        content: string
        relatedType?: string | null
        relatedId?: number | null
      },
    ): MessageRecord {
      const db = getDb()
      const message: MessageRecord = {
        id: nextId(db.messages),
        user_id: userId,
        type: input.type,
        title: input.title,
        content: input.content,
        related_type: input.relatedType ?? null,
        related_id: input.relatedId ?? null,
        is_read: false,
        created_at: formatDateTime(serverNow()),
      }
      db.messages.push(message)
      return message
    }

    /** BR-009 / BR-010：累计违约达到阈值时自动限制 7 天。 */
    export function restrictUser(user: UserRecord, reason: string): BlacklistEntry {
      const db = getDb()
      const now = serverNow()
      const entry: BlacklistEntry = {
        id: nextId(db.blacklist),
        user_id: user.id,
        reason,
        mode: '自动',
        start_at: formatDateTime(now),
        expire_at: formatDateTime(new Date(now.getTime() + RULES.restrictionDays * 86_400_000)),
        released_at: null,
        release_reason: null,
        operator_id: null,
      }
      db.blacklist.push(entry)
      user.account_status = '受限'
      return entry
    }

    /** 重新统计某用户的累计违约次数，保证账户计数与违约记录一致。 */
    export function recountViolations(userId: number): number {
      const db = getDb()
      const user = db.users.find((item) => item.id === userId)
      if (!user) return 0
      user.violation_count = db.violations.filter((item) => item.user_id === userId).length
      return user.violation_count
    }
