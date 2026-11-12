import { describe, expect, it } from 'vitest'

import type { Reservation, Room, Seat } from '@/types'
import {
  BOOKING_RULES,
  bookingDateOptions,
  buildJudgements,
  ceilToStep,
  checkinWindow,
  countdownText,
  dayOffsetFromToday,
  durationText,
  isEffectiveReservation,
  mapBookingFailure,
  minutesToTimeText,
  mySlotUsage,
  occupancyText,
  overlapsSlot,
  parseTimeToMinutes,
  restrictUntilText,
  seatAriaLabel,
  seatCellState,
  shortTime,
  slotMinutes,
  timeOptions,
  timeRangeText,
  todayIso,
  todayText,
  type JudgementContext,
  userBlockReason,
} from '@/utils/bookingRules'

const seat = (overrides: Partial<Seat> = {}): Seat => ({
  id: 1,
  room_id: 1,
  area_id: 1,
  seat_no: 'A-01',
  seat_type: '普通',
  has_power: false,
  near_window: false,
  status: '可用',
  ...overrides,
})

const reservation = (overrides: Partial<Reservation> = {}): Reservation => ({
  id: 1,
  user_id: 1,
  seat_id: 1,
  reserve_date: '2026-11-12',
  start_time: '10:00',
  end_time: '12:00',
  status: '待使用',
  check_in_time: null,
  check_out_time: null,
  cancel_time: null,
  cancel_reason: null,
  created_at: '2026-11-11 10:00:00',
  ...overrides,
})

describe('时间解析与展示', () => {
  it('parseTimeToMinutes 接受合法时间，非法值返回 null', () => {
    expect(parseTimeToMinutes('00:00')).toBe(0)
    expect(parseTimeToMinutes('08:05')).toBe(485)
    expect(parseTimeToMinutes(' 8:05 ')).toBe(485)
    expect(parseTimeToMinutes('24:00')).toBeNull()
    expect(parseTimeToMinutes('08:60')).toBeNull()
    expect(parseTimeToMinutes('')).toBeNull()
    expect(parseTimeToMinutes(null)).toBeNull()
  })

  it('minutesToTimeText 取整并夹在 0–24:00', () => {
    expect(minutesToTimeText(485)).toBe('08:05')
    expect(minutesToTimeText(-1)).toBe('00:00')
    expect(minutesToTimeText(24 * 60 + 30)).toBe('24:00')
    expect(minutesToTimeText(485.6)).toBe('08:06')
  })

  it('shortTime / timeRangeText 统一裁剪秒', () => {
    expect(shortTime('18:30:00')).toBe('18:30')
    expect(shortTime(null)).toBe('')
    expect(timeRangeText('08:00:00', '10:00:00')).toBe('08:00–10:00')
  })

  it('slotMinutes 与 durationText', () => {
    expect(slotMinutes('08:00', '10:30')).toBe(150)
    expect(slotMinutes('10:00', '08:00')).toBe(-120)
    expect(durationText(150)).toBe('2 小时 30 分钟')
    expect(durationText(120)).toBe('2 小时')
    expect(durationText(45)).toBe('45 分钟')
    expect(durationText(0)).toBe('—')
  })
})

describe('时段与日期规则', () => {
  it('overlapsSlot 使用左闭右开口径', () => {
    expect(overlapsSlot(480, 600, 540, 660)).toBe(true)
    expect(overlapsSlot(480, 600, 600, 720)).toBe(false)
    expect(overlapsSlot(600, 720, 480, 600)).toBe(false)
    expect(overlapsSlot(480, 600, 480, 600)).toBe(true)
  })

  it('timeOptions 按粒度生成闭区间候选', () => {
    expect(timeOptions('08:00', '09:00', 5)).toHaveLength(13)
    expect(timeOptions('08:00', '09:00', 5)[0]).toBe('08:00')
    expect(timeOptions('08:00', '09:00', 5).at(-1)).toBe('09:00')
  })

  it('ceilToStep 向上对齐', () => {
    expect(ceilToStep(481, 5)).toBe(485)
    expect(ceilToStep(480, 5)).toBe(480)
    expect(ceilToStep(1)).toBe(BOOKING_RULES.granularity)
  })

  it('bookingDateOptions 从今天起共 8 天，并带今天/明天前缀', () => {
    const now = new Date(2026, 10, 12, 10, 0, 0)
    const options = bookingDateOptions(now)
    expect(options).toHaveLength(BOOKING_RULES.advanceDays + 1)
    expect(options[0].value).toBe('2026-11-12')
    expect(options[0].label).toContain('今天')
    expect(options[1].label).toContain('明天')
    expect(options[2].label).toBe('11-14 周六')
  })

  it('todayIso / todayText / dayOffsetFromToday', () => {
    const now = new Date(2026, 10, 12, 10, 0, 0)
    expect(todayIso(now)).toBe('2026-11-12')
    expect(todayText(now)).toBe('2026-11-12 周四')
    expect(dayOffsetFromToday(now, '2026-11-13')).toBe(1)
    expect(dayOffsetFromToday(now, '2026-11-12')).toBe(0)
    expect(dayOffsetFromToday(now, '2026-11-11')).toBe(-1)
  })
})

describe('签到窗口与倒计时', () => {
  it('签到窗口为开始前 15 分钟至开始后 15 分钟', () => {
    const window = checkinWindow('2026-11-12', '10:00:00')
    expect(window.opensText).toBe('2026-11-12 09:45')
    expect(window.closesText).toBe('2026-11-12 10:15')
    expect(window.rangeText).toBe('09:45–10:15')
    expect(window.closesAt.getTime() - window.opensAt.getTime()).toBe(30 * 60_000)
  })

  it('countdownText 输出 mm:ss / HH:mm:ss / 00:00', () => {
    expect(countdownText(65_000)).toBe('01:05')
    expect(countdownText(3_665_000)).toBe('01:01:05')
    expect(countdownText(0)).toBe('00:00')
    expect(countdownText(Number.NaN)).toBe('00:00')
  })
})

describe('座位状态与本人占用', () => {
  it('seatCellState 优先资源状态，其次临时关闭与占用', () => {
    const available = new Set([1])
    const closed = new Set([2])
    expect(seatCellState(seat({ status: '维修中' }), available)).toBe('fix')
    expect(seatCellState(seat({ status: '停用' }), available)).toBe('off')
    expect(seatCellState(seat({ id: 2 }), available, true, closed)).toBe('closed')
    expect(seatCellState(seat({ id: 1 }), available)).toBe('free')
    expect(seatCellState(seat({ id: 3 }), available)).toBe('taken')
    expect(seatCellState(seat({ id: 1 }), available, false)).toBe('unknown')
  })

  it('seatAriaLabel 同时交代资源状态与时段状态', () => {
    expect(seatAriaLabel(seat(), 'free')).toBe('座位 A-01，资源状态可用，时段可约')
  })

  it('mySlotUsage 统计当日有效预约并找重叠项', () => {
    const usage = mySlotUsage(
      [
        reservation({ id: 1, start_time: '08:00', end_time: '09:00' }),
        reservation({ id: 2, start_time: '11:00', end_time: '13:00' }),
        reservation({ id: 3, status: '已取消', start_time: '10:00', end_time: '12:00' }),
        reservation({ id: 4, reserve_date: '2026-11-13', start_time: '10:00', end_time: '12:00' }),
      ],
      '2026-11-12',
      '10:00',
      '12:00',
    )
    expect(usage.dailyCount).toBe(2)
    expect(usage.conflict?.id).toBe(2)
    expect(userBlockReason(usage)).toBe('C4')
  })

  it('userBlockReason 在无冲突且达到每日上限时返回 C6', () => {
    const usage = mySlotUsage(
      [
        reservation({ id: 1, start_time: '08:00', end_time: '09:00' }),
        reservation({ id: 2, start_time: '09:00', end_time: '10:00' }),
      ],
      '2026-11-12',
      '10:00',
      '12:00',
    )
    expect(usage.conflict).toBeNull()
    expect(usage.dailyCount).toBe(2)
    expect(userBlockReason(usage)).toBe('C6')
  })

  it('isEffectiveReservation 只认待使用与使用中', () => {
    expect(isEffectiveReservation(reservation({ status: '待使用' }))).toBe(true)
    expect(isEffectiveReservation(reservation({ status: '使用中' }))).toBe(true)
    expect(isEffectiveReservation(reservation({ status: '已完成' }))).toBe(false)
    expect(isEffectiveReservation(reservation({ status: '已取消' }))).toBe(false)
    expect(isEffectiveReservation(reservation({ status: '已违约' }))).toBe(false)
  })

  it('occupancyText 区分资源状态、临时关闭与占用', () => {
    expect(occupancyText(seat({ status: '维修中' }), new Set([1]))).toContain('暂无法判断')
    expect(occupancyText(seat(), null, true)).toBe('暂无法判断')
    expect(occupancyText(seat(), new Set([1]), true)).toContain('可约')
    expect(occupancyText(seat(), new Set(), true)).toContain('已被预约')
    expect(occupancyText(seat({ id: 2 }), new Set([2]), true, new Set([2]))).toBe('该时段临时关闭')
  })
})

const room = (overrides: Partial<Room> = {}): Room => ({
  id: 1,
  name: '第一自习室',
  location: '图书馆',
  open_time: '08:00',
  close_time: '22:00',
  capacity: 30,
  enabled: true,
  ...overrides,
})

const judgementCtx = (overrides: Partial<JudgementContext> = {}): JudgementContext => ({
  seat: seat(),
  room: room(),
  reserveDate: '2026-11-12',
  startTime: '10:00',
  endTime: '12:00',
  availableIds: new Set([1]) as ReadonlySet<number> | null,
  usage: { dailyCount: 0, conflict: null },
  accountStatus: '正常',
  restrictUntil: '',
  dayOffset: 0,
  now: new Date(2026, 10, 12, 9, 0, 0),
  ...overrides,
})

describe('buildJudgements C1–C6', () => {
  it('全部满足时六项都通过', () => {
    const items = buildJudgements(judgementCtx())
    expect(items.map((item) => item.id)).toEqual(['C1', 'C2', 'C3', 'C4', 'C5', 'C6'])
    expect(items.every((item) => item.state === 'pass')).toBe(true)
  })

  it('资源不可用 / 已关闭 / 已被占 / 本人冲突 / 账户受限分别对应 C1–C5', () => {
    const c1 = buildJudgements(judgementCtx({ seat: seat({ status: '维修中' }) }))
    expect(c1.find((item) => item.id === 'C1')?.state).toBe('fail')
    expect(c1.find((item) => item.id === 'C3')?.state).toBe('unknown')

    const c2 = buildJudgements(judgementCtx({ room: room({ enabled: false }) }))
    expect(c2.find((item) => item.id === 'C2')?.state).toBe('fail')

    const c3 = buildJudgements(judgementCtx({ availableIds: new Set() }))
    expect(c3.find((item) => item.id === 'C3')?.state).toBe('fail')

    const conflict = reservation({ id: 9, start_time: '10:30', end_time: '11:00' })
    const c4 = buildJudgements(judgementCtx({ usage: { dailyCount: 1, conflict } }))
    expect(c4.find((item) => item.id === 'C4')?.state).toBe('fail')
    expect(c4.find((item) => item.id === 'C4')?.detail).toContain('#9')

    const c5 = buildJudgements(
      judgementCtx({ accountStatus: '受限', restrictUntil: '2026-11-20T10:00:00' }),
    )
    expect(c5.find((item) => item.id === 'C5')?.state).toBe('fail')
    expect(c5.find((item) => item.id === 'C5')?.detail).toContain('预计')
  })

  it('C6 覆盖已开始、超提前天数、超时长与每日上限', () => {
    const started = buildJudgements(judgementCtx({ now: new Date(2026, 10, 12, 10, 30, 0) }))
    expect(started.find((item) => item.id === 'C6')?.state).toBe('fail')
    expect(started.find((item) => item.id === 'C6')?.bullets.join(' ')).toContain('已开始')

    const tooFar = buildJudgements(judgementCtx({ dayOffset: BOOKING_RULES.advanceDays + 1 }))
    expect(tooFar.find((item) => item.id === 'C6')?.state).toBe('fail')

    const tooLong = buildJudgements(judgementCtx({ endTime: '14:05' }))
    expect(tooLong.find((item) => item.id === 'C6')?.state).toBe('fail')

    const dailyLimit = buildJudgements(
      judgementCtx({ usage: { dailyCount: BOOKING_RULES.dailyLimit, conflict: null } }),
    )
    expect(dailyLimit.find((item) => item.id === 'C6')?.state).toBe('fail')
  })
})

describe('mapBookingFailure', () => {
  it('座位冲突归为 C3，且使用固定可读文案', () => {
    const failure = mapBookingFailure(409, { code: 'SEAT_CONFLICT', message: '冲突' })
    expect(failure.kind).toBe('conflict')
    expect(failure.judgement).toBe('C3')
    expect(failure.message).toBe('该时段已被预约，请重新选择')
  })

  it('账户受限保留预计解除时间', () => {
    const failure = mapBookingFailure(403, {
      code: 'ACCOUNT_RESTRICTED',
      message: '账户受限',
      restrict_until: '2026-11-20T10:00:00',
    })
    expect(failure.kind).toBe('restricted')
    expect(failure.judgement).toBe('C5')
    expect(failure.restrictUntil).toBe('2026-11-20T10:00:00')
    expect(restrictUntilText(failure.restrictUntil)).toBe('2026-11-20 10:00')
  })

  it('已开始时段归为 expired，并清理服务端提示里的需求编号', () => {
    const failure = mapBookingFailure(409, {
      code: 'TIME_STARTED',
      message: '该时段已开始，不能预约（ST-029）；有效预约不可重复',
    })
    expect(failure.kind).toBe('expired')
    expect(failure.message).not.toContain('ST-029')
    expect(failure.message).not.toContain('有效预约')
  })

  it('未知错误归为 rule 并保留 HTTP 状态', () => {
    const failure = mapBookingFailure(500, { detail: '服务异常' })
    expect(failure.kind).toBe('rule')
    expect(failure.code).toBe('HTTP_500')
    expect(failure.message).toBe('服务异常')
  })
})
