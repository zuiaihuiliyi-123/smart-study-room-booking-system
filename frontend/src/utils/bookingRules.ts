/**
 * 预约座位的展示口径、本地预检与失败归类（FR-010 / FR-012 / FR-013）。
 *
 * 依据：
 * - 需求规格说明书（课程结构版）第 4.3 节时间边界判定表、第 4.4.2 节可预约性判定项 C1～C6
 * - AGENTS.md §4：左闭右开 `[s, e)`、粒度 30 分钟、提前上限 7 天、单次上限 4 小时、
 *   每人每日 2 条有效预约、签到窗口「开始前 15 分钟至开始后 15 分钟」
 *
 * 边界说明：本文件只做**界面渲染 + 提交前的本地预估**。权威判定在服务端
 * （`backend/app/core/config.py` 与 FR-012 的服务端实现）；提交后一律以服务端返回的
 * `code` / `rule` / `message` 覆盖本地结论（见 `mapBookingFailure`）。
 */
import dayjs from 'dayjs'

import type { Reservation, Room, Seat } from '@/types'

/** 参数基线：与 AGENTS.md §4 及 backend/app/core/config.py 保持一致，改动须同步核对。 */
export const BOOKING_RULES = {
  /** BR-001 预约粒度（分钟） */
  granularity: 30,
  /** BR-002 最多提前预约天数 */
  advanceDays: 7,
  /** BR-003 单次预约时长上限（小时） */
  maxHours: 4,
  /** BR-004 每人每日有效预约上限（条） */
  dailyLimit: 2,
  /** BR-007 签到窗口：开始前（分钟） */
  checkinEarly: 15,
  /** BR-007 签到窗口：开始后（分钟） */
  checkinLate: 15,
  /** BR-011 无损取消门槛：距开始（分钟） */
  cancelBefore: 30,
  /** BR-009 累计**有效**违约次数阈值（达到即触发限制） */
  violationThreshold: 3,
  /** BR-010 触发限制后的限制天数（期满自动解除） */
  restrictionDays: 7,
} as const

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'] as const

/* ------------------------------------------------------------------ 时段与日期 */

export function parseTimeToMinutes(value: string | null | undefined): number | null {
  if (!value) return null
  const match = /^(\d{1,2}):(\d{2})/.exec(value.trim())
  if (!match) return null
  const hour = Number(match[1])
  const minute = Number(match[2])
  if (hour > 23 || minute > 59) return null
  return hour * 60 + minute
}

export function minutesToTimeText(minutes: number): string {
  const safe = Math.max(0, Math.min(24 * 60, Math.round(minutes)))
  const hour = Math.floor(safe / 60)
  const minute = safe % 60
  return `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`
}

/** 统一把接口返回的 `HH:MM:SS` 与表单里的 `HH:MM` 裁成 `HH:MM` 展示。 */
export function shortTime(value: string | null | undefined): string {
  return (value ?? '').slice(0, 5)
}

/** 形如 `18:30–20:30`；区间口径为左闭右开 `[s, e)`。 */
export function timeRangeText(startTime: string, endTime: string): string {
  return `${shortTime(startTime)}–${shortTime(endTime)}`
}

/** 形如 `[14:00, 16:00)`：把左闭右开口径直接写进文案（预约列表的「时段」列）。 */
export function bracketRangeText(startTime: string, endTime: string): string {
  return `[${shortTime(startTime)}, ${shortTime(endTime)})`
}

/** 预约开始时刻；日期或时间不合法时返回 null（不猜测缺省值）。 */
export function slotStartAt(reserveDate: string, startTime: string): Date | null {
  if (!reserveDate || !startTime) return null
  const parsed = dayjs(`${reserveDate} ${shortTime(startTime)}`)
  return parsed.isValid() ? parsed.toDate() : null
}

/** BR-011 无损取消截止时刻 = 开始时刻 − 30 分钟。 */
export function cancelDeadlineAt(reserveDate: string, startTime: string): Date | null {
  const start = slotStartAt(reserveDate, startTime)
  return start === null ? null : new Date(start.getTime() - BOOKING_RULES.cancelBefore * 60_000)
}

export function slotMinutes(startTime: string, endTime: string): number {
  const start = parseTimeToMinutes(startTime)
  const end = parseTimeToMinutes(endTime)
  if (start === null || end === null) return 0
  return end - start
}

export function durationText(minutes: number): string {
  if (minutes <= 0) return '—'
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (hours === 0) return `${rest} 分钟`
  if (rest === 0) return `${hours} 小时`
  return `${hours} 小时 ${rest} 分钟`
}

/** BR-020：重叠当且仅当 `s₁ < e₂ ∧ s₂ < e₁`。 */
export function overlapsSlot(
  aStart: number,
  aEnd: number,
  bStart: number,
  bEnd: number,
): boolean {
  return aStart < bEnd && bStart < aEnd
}

/** `el-time-select` 的候选项：从开放到闭馆按粒度步进。 */
export function timeOptions(
  startTime: string,
  endTime: string,
  step: number = BOOKING_RULES.granularity,
): string[] {
  const start = parseTimeToMinutes(startTime) ?? 8 * 60
  const end = parseTimeToMinutes(endTime) ?? 22 * 60
  const options: string[] = []
  for (let minute = start; minute <= end; minute += step) {
    options.push(minutesToTimeText(minute))
  }
  return options
}

/** 把 `HH:MM` 对齐到粒度（向上取整），用于默认开始时间。 */
export function ceilToStep(minutes: number, step: number = BOOKING_RULES.granularity): number {
  return Math.ceil(minutes / step) * step
}

export interface DateOption {
  value: string
  label: string
}

/** 日期候选：今天起 `advanceDays` 天内（含今天），共 8 项。 */
export function bookingDateOptions(now: Date): DateOption[] {
  const today = dayjs(now).startOf('day')
  const options: DateOption[] = []
  for (let offset = 0; offset <= BOOKING_RULES.advanceDays; offset += 1) {
    const day = today.add(offset, 'day')
    const weekday = WEEKDAYS[day.day()]
    const prefix = offset === 0 ? '今天' : offset === 1 ? '明天' : ''
    options.push({
      value: day.format('YYYY-MM-DD'),
      label: `${prefix ? `${prefix} · ` : ''}${day.format('MM-DD')} ${weekday}`,
    })
}
return options
}

export function todayIso(now: Date): string {
  return dayjs(now).format('YYYY-MM-DD')
}

export function todayText(now: Date): string {
  const day = dayjs(now)
  return `${day.format('YYYY-MM-DD')} ${WEEKDAYS[day.day()]}`
}

export function dayOffsetFromToday(now: Date, dateIso: string): number {
  return dayjs(dateIso).startOf('day').diff(dayjs(now).startOf('day'), 'day')
}

/* ------------------------------------------------------------------ 签到窗口 */

export interface CheckinWindow {
  opensAt: Date
  closesAt: Date
  /** `YYYY-MM-DD HH:mm` */
  opensText: string
  closesText: string
  /** `18:15–18:45` */
  rangeText: string
}

/** BR-007：签到窗口 `[s − 15 分钟, s + 15 分钟)`。 */
export function checkinWindow(reserveDate: string, startTime: string): CheckinWindow {
  const start = dayjs(`${reserveDate} ${shortTime(startTime)}`)
  const opensAt = start.subtract(BOOKING_RULES.checkinEarly, 'minute')
  const closesAt = start.add(BOOKING_RULES.checkinLate, 'minute')
  return {
    opensAt: opensAt.toDate(),
    closesAt: closesAt.toDate(),
    opensText: opensAt.format('YYYY-MM-DD HH:mm'),
    closesText: closesAt.format('YYYY-MM-DD HH:mm'),
    rangeText: timeRangeText(opensAt.format('HH:mm'), closesAt.format('HH:mm')),
  }
}

export function countdownText(ms: number): string {
  if (!Number.isFinite(ms) || ms <= 0) return '00:00'
  const total = Math.floor(ms / 1000)
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const seconds = total % 60
  const pad = (value: number) => String(value).padStart(2, '0')
  return hours > 0
    ? `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`
    : `${pad(minutes)}:${pad(seconds)}`
}

/* ------------------------------------------------------------------ 座位四态 */

/** 矩阵单元格的复合视觉态：free / taken 来自时段占用，fix / off 来自资源状态。 */
export type SeatCellState = 'free' | 'taken' | 'fix' | 'off'

export const SEAT_STATE_TEXT: Record<SeatCellState, string> = {
  free: '可约',
  taken: '该时段已被预约',
  fix: '维修中',
  off: '停用',
}

export const SEAT_STATE_ORDER: readonly SeatCellState[] = ['free', 'taken', 'fix', 'off']

/** 有效预约 = 待使用 | 使用中；已取消 / 已完成 / 已违约不占用时段（TM-18）。 */
export function isEffectiveReservation(item: Reservation): boolean {
  return item.status === '待使用' || item.status === '使用中'
}

/**
 * 单元格视觉态。
 * 资源状态非「可用」时 C1 先行不通过，按时段判定无意义，故直接呈现资源状态。
 */
export function seatCellState(seat: Seat, availableIds: ReadonlySet<number>): SeatCellState {
  if (seat.status === '维修中') return 'fix'
  if (seat.status === '停用') return 'off'
  return availableIds.has(seat.id) ? 'free' : 'taken'
}

/** tooltip 的「时段占用」一行：与资源状态分开呈现，不合并成一个状态（AGENTS.md §4）。 */
export function occupancyText(seat: Seat, availableIds: ReadonlySet<number> | null): string {
  if (seat.status !== '可用') {
    return '未判定（资源状态非「可用」，接口不返回该座位的占用信息）'
  }
  if (availableIds === null) return '未判定'
  return availableIds.has(seat.id)
    ? '可约（该时段不存在其他有效预约）'
    : '已被预约（该时段存在其他有效预约）'
}

export function seatAriaLabel(seat: Seat, state: SeatCellState): string {
  return `座位 ${seat.seat_no}，资源状态${seat.status}，时段${SEAT_STATE_TEXT[state]}`
}

/* ------------------------------------------------------------------ 本人时段占用 */

export interface MySlotUsage {
  /** 当日有效预约条数（BR-004 计数口径） */
  dailyCount: number
  /** 与目标时段重叠的本人有效预约（BR-005 / C4） */
  conflict: Reservation | null
}

export function mySlotUsage(
  reservations: readonly Reservation[],
  reserveDate: string,
  startTime: string,
  endTime: string,
): MySlotUsage {
  const start = parseTimeToMinutes(startTime) ?? 0
  const end = parseTimeToMinutes(endTime) ?? 0
  const sameDay = reservations.filter(
    (item) => item.reserve_date === reserveDate && isEffectiveReservation(item),
  )
  const conflict =
    sameDay.find((item) =>
      overlapsSlot(
      start,
      end,
      parseTimeToMinutes(item.start_time) ?? 0,
      parseTimeToMinutes(item.end_time) ?? 0,
    ),
  ) ?? null
  return { dailyCount: sameDay.length, conflict }
}

/** C4 优先于 C6：与 mock / 服务端的判定顺序一致，保证界面结论可解释。 */
export function userBlockReason(usage: MySlotUsage): 'C4' | 'C6' | null {
  if (usage.conflict) return 'C4'
  if (usage.dailyCount >= BOOKING_RULES.dailyLimit) return 'C6'
  return null
}

/* ------------------------------------------------------------------ C1～C6 */

export type JudgementId = 'C1' | 'C2' | 'C3' | 'C4' | 'C5' | 'C6'
export type JudgementState = 'pass' | 'fail' | 'unknown'

export interface JudgementItem {
  id: JudgementId
  title: string
  /** 第 4.4.2 节表格的判定条件原文，界面直接展示，避免改写口径 */
  condition: string
  rules: readonly string[]
  state: JudgementState
  detail: string
  /** 附加的逐条参数说明（C6 的四条子规则） */
  bullets: readonly string[]
}

export interface JudgementContext {
  seat: Seat
  room: Room
  reserveDate: string
  startTime: string
  endTime: string
  /** 可预约座位集合；null 表示本次查询未取得（此时 C3 记「未判定」） */
  availableIds: ReadonlySet<number> | null
  usage: MySlotUsage
  accountStatus: string
  /** 受限账户的预计解除时间（来自服务端 403 响应体） */
  restrictUntil: string
  dayOffset: number
}

export function buildJudgements(ctx: JudgementContext): JudgementItem[] {
  const { seat, room, startTime, endTime, availableIds, usage } = ctx
  const start = parseTimeToMinutes(startTime) ?? 0
  const end = parseTimeToMinutes(endTime) ?? 0
  const open = parseTimeToMinutes(room.open_time) ?? 0
  const close = parseTimeToMinutes(room.close_time) ?? 0
  const range = timeRangeText(startTime, endTime)
  const minutes = Math.max(0, end - start)

  const c1Pass = seat.status === '可用'
  const c2Pass = room.enabled && start >= open && end <= close && end > start
  const c3State: JudgementState =
    seat.status !== '可用' || availableIds === null
    ? 'unknown'
    : availableIds.has(seat.id)
    ? 'pass'
    : 'fail'
  const c4Pass = usage.conflict === null
  const c5Pass = ctx.accountStatus === '正常'
  const aligned =
    start % BOOKING_RULES.granularity === 0 && end % BOOKING_RULES.granularity === 0
  const advanceOk = ctx.dayOffset >= 0 && ctx.dayOffset <= BOOKING_RULES.advanceDays
  const durationOk = minutes > 0 && minutes <= BOOKING_RULES.maxHours * 60
  const dailyOk = usage.dailyCount < BOOKING_RULES.dailyLimit
  const c6Pass = aligned && advanceOk && durationOk && dailyOk

  return [
    {
      id: 'C1',
      title: '资源状态',
      condition: '座位资源状态 = “可用”',
      rules: [''],
      state: c1Pass ? 'pass' : 'fail',
      detail: c1Pass
        ? `座位 ${seat.seat_no} 资源状态为「可用」`
        : `座位 ${seat.seat_no} 资源状态为「${seat.status}」，维修中 / 停用的座位不可被预约`,
      bullets: [],
    },
    {
      id: 'C2',
      title: '所属自习室',
      condition: '所属自习室处于启用状态，且目标时段落在开放时间内',
      rules: [],
      state: c2Pass ? 'pass' : 'fail',
      detail: c2Pass
        ? `${room.name} 处于启用状态，开放时间 ${shortTime(room.open_time)}–${shortTime(room.close_time)}，所选时段 ${range} 落在开放时间内`
        : `${room.name}${room.enabled ? '' : ' 当前未启用'}；开放时间 ${shortTime(room.open_time)}–${shortTime(room.close_time)}，所选时段 ${range} 不在可预约范围内`,
      bullets: [],
    },
    {
      id: 'C3',
      title: '座位时段占用',
      condition: '不存在其他有效预约单，其占用区间与目标区间满足 s_new < e_old ∧ s_old < e_new',
      rules: [''],
      state: c3State,
      detail:
      c3State === 'pass'
        ? `座位 ${seat.seat_no} 在 ${range} 无其他有效预约`
        : c3State === 'fail'
        ? `座位 ${seat.seat_no} 在 ${range} 已被其他有效预约占用`
        : '未判定：资源状态非「可用」或本次查询未返回可用座位集合',
      bullets: ['左闭右开 [s, e)：相邻时段（如 18:30–20:30 与 20:30–21:30）不冲突'],
    },
    {
      id: 'C4',
      title: '用户时段占用',
      condition: '该用户在同一时段不存在其他有效预约单',
      rules: [''],
      state: c4Pass ? 'pass' : 'fail',
      detail: c4Pass
        ? `你在 ${ctx.reserveDate} ${range} 没有其他有效预约`
        : `你已有预约单 #${usage.conflict?.id ?? '-'}（${timeRangeText(
                  usage.conflict?.start_time ?? '',
                  usage.conflict?.end_time ?? '',
                )}）与该时段重叠，同一用户同一时段不得存在两条有效预约`,
        bullets: [],
      },
      {
        id: 'C5',
        title: '用户资格',
        condition: '账户状态 = “正常”',
        rules: ['', '', ''],
        state: c5Pass ? 'pass' : 'fail',
        detail: c5Pass
          ? '账户状态为「正常」'
          : `账户状态为「${ctx.accountStatus}」${ctx.restrictUntil ? `，预计 ${ctx.restrictUntil} 解除限制` : ''}，暂不可预约`,
        bullets: [],
      },
      {
        id: 'C6',
        title: '规则约束',
        condition: '四个约束全部满足：粒度对齐、提前天数、单次时长、每日次数',
        rules: [],
        state: c6Pass ? 'pass' : 'fail',
        detail: c6Pass ? '四条规则约束全部满足' : '存在未满足的规则约束，详见下方逐条参数',
        bullets: [
          `粒度：须对齐 ${BOOKING_RULES.granularity} 分钟 —— ${aligned ? '已对齐' : `未对齐（${range}）`}`,
          `提前天数：最多提前 ${BOOKING_RULES.advanceDays} 天 —— 所选日期为第 ${ctx.dayOffset} 天（${advanceOk ? '符合' : '超出范围'}）`,
          `单次时长：上限 ${BOOKING_RULES.maxHours} 小时 —— 本次 ${durationText(minutes)}（${durationOk ? '符合' : '超出上限'}）`,
          `每日次数：每人每日最多 ${BOOKING_RULES.dailyLimit} 条有效预约 —— 当日已 ${usage.dailyCount} 条（${dailyOk ? '符合' : '已达上限'}）`,
        ],
      },
    ]
  }

  /* ------------------------------------------------------------------ 失败归类 */

  export type BookingFailureKind = 'conflict' | 'restricted' | 'rule' | 'expired' | 'unknown'

  export interface BookingFailure {
    kind: BookingFailureKind
    message: string
    /** 失败归属的判定项；无法归属时为 null（如并发占用、时段已过期） */
    judgement: JudgementId | null
    code: string
    rule: string
    /** 受限账户的预计解除时间（服务端下发，形如 `2026-11-05T18:02:00`） */
    restrictUntil: string
  }

  /** 服务端错误体：业务错误为 `{ code, message, ...extra }`，鉴权错误为 `{ detail }`。 */
  const CODE_TO_JUDGEMENT: Record<string, JudgementId> = {
    SEAT_UNAVAILABLE: 'C1',
    ROOM_UNAVAILABLE: 'C2',
    OUT_OF_OPEN_HOURS: 'C2',
    SEAT_CONFLICT: 'C3',
    USER_CONFLICT: 'C4',
    ACCOUNT_RESTRICTED: 'C5',
    ACCOUNT_DISABLED: 'C5',
    TIME_NOT_ALIGNED: 'C6',
    DURATION_EXCEEDED: 'C6',
    DATE_OUT_OF_RANGE: 'C6',
    DAILY_LIMIT: 'C6',
  }

  const RULE_TO_JUDGEMENT: Record<string, JudgementId> = {
    '': 'C1',
    '': 'C3',
    '': 'C4',
    '': 'C5',
    '': 'C5',
    '': 'C6',
    '': 'C6',
    '': 'C6',
    '': 'C6',
  }

  function asText(value: unknown): string {
    return typeof value === 'string' ? value : ''
  }

  function bodyOf(data: unknown): Record<string, unknown> {
    return data !== null && typeof data === 'object' ? (data as Record<string, unknown>) : {}
  }

  /** 把 axios 错误（status + 响应体）归类为界面可直接渲染的失败描述。 */
  export function mapBookingFailure(status: number | undefined, data: unknown): BookingFailure {
    const body = bodyOf(data)
    const code = asText(body.code)
    const rule = asText(body.rule)
    const serverMessage = asText(body.message) || asText(body.detail)
    const restrictUntil = asText(body.restrict_until)

    // FR-014 / NFR-003：并发写入冲突（至多一条成功），文案固定，便于用户直接改选时段
    if (status === 409 || code === 'CONCURRENT_CONFLICT') {
      return {
        kind: 'conflict',
        message: '该时段已被预约，请重新选择',
        judgement: null,
        code: code || 'CONCURRENT_CONFLICT',
        rule,
        restrictUntil,
      }
    }

    // ST-047：受限账户提示限制原因与预计解除时间；停用账户不展示预计时间
    if (code === 'ACCOUNT_RESTRICTED' || code === 'ACCOUNT_DISABLED') {
      return {
        kind: 'restricted',
        message: serverMessage || '账户当前处于受限状态，暂不可预约',
        judgement: 'C5',
        code,
        rule,
        restrictUntil,
      }
    }

    // FR-013 E2：所选时段已过期
    if (code === 'TIME_STARTED') {
      return {
        kind: 'expired',
        message: serverMessage || '该时段已经开始，不能预约，请重新选择时段',
        judgement: null,
        code,
        rule,
        restrictUntil,
      }
    }

    return {
      kind: 'rule',
      message: serverMessage || '提交失败，请稍后重试',
      judgement: CODE_TO_JUDGEMENT[code] ?? RULE_TO_JUDGEMENT[rule] ?? null,
      code: code || `HTTP_${status ?? 0}`,
      rule,
      restrictUntil,
    }
  }

  /** 受限原因与预计解除时间的展示文案（403 响应体的 `restrict_until`）。 */
  export function restrictUntilText(value: string): string {
    if (!value) return ''
    const parsed = dayjs(value)
    return parsed.isValid() ? parsed.format('YYYY-MM-DD HH:mm') : value
  }
