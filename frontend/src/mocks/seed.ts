/**
 * 种子数据：3 个自习室 × 3 个分区 × 10 个座位、4 名学生 + 2 名管理员，
 * 预约覆盖 5 种状态（含相邻时段 [14:00,16:00) / [16:00,18:00) 同座位）、
 * 自动与手动违约、5 种投诉状态、未读站内消息、近 7 天看板数据。
 *
 * 日期均以「服务器时间」（serverNow，可由 __ssrMock.setTimeOffset 偏移）为基准，
 * 因此任何时刻启动都能得到形状完整、规则自洽的数据。
 */
import type {
  Area,
  BlacklistEntry,
  Complaint,
  Reservation,
  Review,
  Room,
  Seat,
  Violation,
} from '@/types'

import type { MockDb, MessageRecord, ReservationRecord, UserRecord } from './db'
import {
  addDays,
  addMinutes,
  ceilToStep,
  combine,
  floorToStep,
  formatDate,
  formatDateTime,
  minutesToTime,
  parseTimeMinutes,
  serverNow,
  startOfDay,
} from './time'

const OPEN = 8 * 60
const CLOSE = 22 * 60
const STEP = 30

interface AreaSpec {
  prefix: string
  name: string
  seatType: string
}

const ROOM_SPECS: Array<{ id: number; name: string; location: string; areas: AreaSpec[] }> = [
  {
    id: 1,
    name: '第一自习室',
    location: '图书馆 A 区 3 楼',
    areas: [
      { prefix: 'A', name: '静音区', seatType: '普通' },
      { prefix: 'B', name: '靠窗区', seatType: '靠窗' },
      { prefix: 'C', name: '电源区', seatType: '带电源' },
    ],
  },
  {
    id: 2,
    name: '第二自习室',
    location: '图书馆 B 区 2 楼',
    areas: [
      { prefix: 'D', name: '静音区', seatType: '普通' },
      { prefix: 'E', name: '靠窗区', seatType: '靠窗' },
      { prefix: 'F', name: '电源区', seatType: '带电源' },
    ],
  },
  {
    id: 3,
    name: '第三自习室',
    location: '教学楼 C 座 101',
    areas: [
      { prefix: 'G', name: '静音区', seatType: '普通' },
      { prefix: 'H', name: '靠窗区', seatType: '靠窗' },
      { prefix: 'I', name: '电源区', seatType: '带电源' },
    ],
  },
]

/** 非「可用」的座位样本（资源状态与预约状态是两个维度，见 AGENTS.md §4）。 */
const SEAT_STATUS: Record<string, Seat['status']> = {
  'B-07': '维修中',
  'E-03': '维修中',
  'I-10': '停用',
}

const DEMO_PASSWORD = 'student123'

function buildUsers(): UserRecord[] {
  const base = [
    { id: 1, name: '演示学生', student_no: 'student', password: DEMO_PASSWORD, role: '学生用户', status: '正常', contact: '13800001234' },
    { id: 2, name: '陈嘉禾', student_no: '3200104521', password: DEMO_PASSWORD, role: '学生用户', status: '正常', contact: '13900002345' },
    { id: 3, name: '苏亦然', student_no: '3200104522', password: DEMO_PASSWORD, role: '学生用户', status: '正常', contact: '13700003456' },
    { id: 4, name: '郑一诺', student_no: '3200104523', password: DEMO_PASSWORD, role: '学生用户', status: '受限', contact: '13600004567' },
    { id: 5, name: '王管理员', student_no: 'admin', password: 'admin123', role: '自习室管理员', status: '正常', contact: '13500005678' },
    { id: 6, name: '李明', student_no: 'sysadmin', password: 'admin123', role: '系统管理员', status: '正常', contact: null },
  ] as const

  return base.map((item) => ({
    id: item.id,
    name: item.name,
    student_no: item.student_no,
    password: item.password,
    role: item.role,
    account_status: item.status,
    violation_count: 0,
    contact: item.contact,
    created_at: formatDateTime(addDays(serverNow(), -180)),
  }))
}

interface ReservationSeed {
  user: number
  seatNo: string
  day: Date
  start: number
  end: number
  status: Reservation['status']
  createdAt: Date
  checkIn?: number
  checkOut?: number
  cancelAt?: Date
  cancelReason?: string
}

export function buildSeed(): MockDb {
  const now = serverNow()
  const today = startOfDay(now)

  const users = buildUsers()
  const rooms: Room[] = []
  const areas: Area[] = []
  const seats: Seat[] = []

  let areaId = 1
  let seatId = 1
  for (const spec of ROOM_SPECS) {
    rooms.push({
      id: spec.id,
      name: spec.name,
      location: spec.location,
      open_time: '08:00',
      close_time: '22:00',
      capacity: spec.areas.length * 10,
      enabled: true,
    })
  for (const block of spec.areas) {
    areas.push({ id: areaId, room_id: spec.id, name: block.name })
    for (let index = 1; index <= 10; index += 1) {
      const seatNo = `${block.prefix}-${String(index).padStart(2, '0')}`
        seats.push({
          id: seatId,
          room_id: spec.id,
          area_id: areaId,
          seat_no: seatNo,
          seat_type: block.seatType,
          has_power: block.seatType === '带电源' || (block.seatType === '靠窗' && index % 4 === 0),
          status: SEAT_STATUS[seatNo] ?? '可用',
        })
        seatId += 1
      }
      areaId += 1
    }
  }

  const reservations: ReservationRecord[] = []
  const violations: Violation[] = []
  let reservationSeq = 1
  let violationSeq = 1

  const seatByNo = new Map(seats.map((seat) => [seat.seat_no, seat]))
  function seatIdOf(seatNo: string): number {
    const seat = seatByNo.get(seatNo)
    if (!seat) throw new Error(`种子数据引用了不存在的座位：${seatNo}`)
      return seat.id
    }

    function pushReservation(seed: ReservationSeed): ReservationRecord {
      const record: ReservationRecord = {
        id: reservationSeq,
        user_id: seed.user,
        seat_id: seatIdOf(seed.seatNo),
        reserve_date: formatDate(seed.day),
        start_time: minutesToTime(seed.start),
        end_time: minutesToTime(seed.end),
        status: seed.status,
        check_in_time: seed.checkIn === undefined ? null : formatDateTime(combine(seed.day, seed.checkIn)),
        check_out_time: seed.checkOut === undefined ? null : formatDateTime(combine(seed.day, seed.checkOut)),
        cancel_time: seed.cancelAt === undefined ? null : formatDateTime(seed.cancelAt),
        cancel_reason: seed.cancelReason ?? null,
        created_at: formatDateTime(seed.createdAt),
        idempotency_key: `seed-${reservationSeq}`,
      updated_at: formatDateTime(seed.createdAt),
    }
    reservations.push(record)
    reservationSeq += 1
    return record
  }

  function hasConflict(seatNo: string, day: Date, start: number, end: number): boolean {
    const date = formatDate(day)
    const id = seatIdOf(seatNo)
    return reservations.some((item) => {
      if (item.seat_id !== id || item.reserve_date !== date) return false
      if (item.status !== '待使用' && item.status !== '使用中' && item.status !== '已完成') return false
      const itemStart = parseTimeMinutes(item.start_time) ?? 0
      const itemEnd = parseTimeMinutes(item.end_time) ?? 0
      return start < itemEnd && itemStart < end
    })
  }

  // ① 违约样本：6 条历史（自动 + 手动）+ 2 条今日凌晨判定的逾期未签到
  const violationSeeds: Array<{
    user: number
    seatNo: string
    dayOffset: number
    start: number
    end: number
    type: Violation['type']
    operator: number | null
    detectedDayOffset: number
    detectedMinute: number
    checkedIn: boolean
  }> = [
    { user: 1, seatNo: 'A-03', dayOffset: -2, start: 540, end: 660, type: '自动违约', operator: null, detectedDayOffset: -2, detectedMinute: 676, checkedIn: false },
    { user: 3, seatNo: 'E-02', dayOffset: -1, start: 600, end: 720, type: '自动违约', operator: null, detectedDayOffset: -1, detectedMinute: 736, checkedIn: false },
    { user: 3, seatNo: 'D-04', dayOffset: -1, start: 840, end: 960, type: '手动违约', operator: 5, detectedDayOffset: -1, detectedMinute: 900, checkedIn: true },
    { user: 4, seatNo: 'G-05', dayOffset: -3, start: 540, end: 660, type: '自动违约', operator: null, detectedDayOffset: -3, detectedMinute: 676, checkedIn: false },
    { user: 4, seatNo: 'H-06', dayOffset: -2, start: 780, end: 900, type: '自动违约', operator: null, detectedDayOffset: -2, detectedMinute: 916, checkedIn: false },
    { user: 4, seatNo: 'I-02', dayOffset: -1, start: 900, end: 1020, type: '自动违约', operator: null, detectedDayOffset: -1, detectedMinute: 1036, checkedIn: false },
    { user: 1, seatNo: 'B-02', dayOffset: -1, start: 1140, end: 1260, type: '自动违约', operator: null, detectedDayOffset: 0, detectedMinute: 5, checkedIn: false },
    { user: 4, seatNo: 'G-08', dayOffset: -1, start: 780, end: 900, type: '自动违约', operator: null, detectedDayOffset: 0, detectedMinute: 6, checkedIn: false },
  ]

  for (const seed of violationSeeds) {
    const day = addDays(today, seed.dayOffset)
    const record = pushReservation({
      user: seed.user,
      seatNo: seed.seatNo,
      day,
      start: seed.start,
      end: seed.end,
      status: '已违约',
      createdAt: combine(addDays(day, -1), 20 * 60),
      checkIn: seed.checkedIn ? seed.start + 2 : undefined,
    })
    violations.push({
      id: violationSeq,
      user_id: seed.user,
      reservation_id: record.id,
      type: seed.type,
      reason:
        seed.type === '自动违约'
          ? '超过签到截止时间仍未签到，系统自动判定违约'
          : '现场巡查发现超时占座并影响他人，管理员登记',
      operator_id: seed.operator,
      created_at: formatDateTime(combine(addDays(today, seed.detectedDayOffset), seed.detectedMinute)),
    })
    violationSeq += 1
  }

  // ② 近 7 天的已完成预约：看板「各座位已使用时段数」与折线图的数据形状来源
  const hotSeats = seats.filter((seat) => seat.status === '可用').slice(0, 36)
  for (let offset = 6; offset >= 1; offset -= 1) {
    const day = addDays(today, -offset)
    for (let index = 0; index < 18; index += 1) {
      const seat = hotSeats[(offset * 7 + index * 11) % hotSeats.length]
      const start = OPEN + ((offset * 3 + index * 5) % 20) * STEP
      const slots = 2 + ((offset + index) % 5)
      const end = Math.min(start + slots * STEP, CLOSE)
      if (end - start < STEP) continue
      if (hasConflict(seat.seat_no, day, start, end)) continue
      pushReservation({
        user: ((offset + index) % 4) + 1,
        seatNo: seat.seat_no,
        day,
        start,
        end,
        status: '已完成',
        createdAt: combine(day, Math.max(0, start - 30)),
        checkIn: start + 3,
        checkOut: end - 4,
      })
    }
  }

  // ③ 今日/明日预约：覆盖 5 种状态、相邻时段占用、签到窗口与受限账户既有预约
  const demo = demoTarget(now, today)

  const currentStart = floorToStep(now, STEP) - STEP
  let studentInUse: ReservationRecord | null = null
  if (currentStart >= OPEN && currentStart + 90 <= CLOSE) {
    studentInUse = pushReservation({
      user: 1,
      seatNo: 'D-05',
      day: today,
      start: currentStart,
      end: currentStart + 90,
      status: '使用中',
      createdAt: combine(today, OPEN),
      checkIn: currentStart + 4,
    })
  }

  const cancelTarget = demo.start + 120
  let cancelled: ReservationRecord | null = null
  if (cancelTarget + 60 <= CLOSE) {
    cancelled = pushReservation({
      user: 1,
      seatNo: 'A-02',
      day: demo.day,
      start: cancelTarget,
      end: cancelTarget + 60,
      status: '已取消',
      createdAt: addMinutes(now, -30),
      cancelAt: addMinutes(now, -25),
      cancelReason: '临时有事，提前取消',
    })
  }

  // 同一座位 [A, A+2h) 已被占用：验证左闭右开下 [A+2h, A+4h) 仍可预约（BR-020）
  const hold = pushReservation({
    user: 3,
    seatNo: 'A-01',
    day: demo.day,
    start: demo.start,
    end: demo.start + 120,
    status: '待使用',
    createdAt: now,
  })

  const laterStart = demo.start + 120
  if (laterStart + 60 <= CLOSE) {
    pushReservation({
      user: 2,
      seatNo: 'F-04',
      day: demo.day,
      start: laterStart,
      end: laterStart + 60,
      status: '待使用',
      createdAt: now,
    })
  }

  const restrictedStart = demo.start + 30
  if (restrictedStart + 60 <= CLOSE) {
    pushReservation({
      user: 4,
      seatNo: 'G-02',
      day: demo.day,
      start: restrictedStart,
      end: restrictedStart + 60,
      status: '待使用',
      createdAt: now,
    })
  }

  // ④ 已取消（历史）：说明「已取消不占用时段」
  pushReservation({
    user: 2,
    seatNo: 'C-02',
    day: addDays(today, -3),
    start: 1080,
    end: 1200,
    status: '已取消',
    createdAt: combine(addDays(today, -4), 21 * 60),
    cancelAt: addDays(today, -3),
    cancelReason: '课程调整，取消预约',
  })

  // ⑤ 评价（仅「已完成」可评，一单一评）
  const reviewSeeds: Array<{ user: number; score: number; content: string | null }> = [
    { user: 1, score: 5, content: '靠窗安静，插座可用，闭馆前有人巡查。' },
    { user: 3, score: 4, content: '座位整洁，空调略冷。' },
    { user: 2, score: 3, content: null },
  ]
  const reviews: Review[] = []
  for (const seed of reviewSeeds) {
    const target = reservations.find(
      (item) => item.user_id === seed.user && item.status === '已完成',
    )
    if (!target) continue
    reviews.push({
      id: reviews.length + 1,
      user_id: seed.user,
      reservation_id: target.id,
      score: seed.score,
      content: seed.content,
      created_at: target.check_out_time ?? target.created_at,
    })
  }

  // ⑥ 投诉：5 种状态齐备
  const complaints: Complaint[] = [
    {
      id: 1,
      user_id: 1,
      target_type: '座位',
      target_id: seatIdOf('D-05'),
      content: '该座位台灯不亮，希望安排维修。',
      status: '待处理',
      handler_id: null,
      handle_note: null,
      handled_at: null,
      created_at: formatDateTime(addMinutes(now, -26 * 60)),
    },
    {
      id: 2,
      user_id: 1,
      target_type: '自习室',
      target_id: 1,
      content: 'A 区空调温度过低，建议调整。',
      status: '已处理',
      handler_id: 5,
      handle_note: '已联系物业调整设定温度，并张贴提示。',
      handled_at: formatDateTime(addDays(now, -2)),
      created_at: formatDateTime(addDays(now, -3)),
    },
    {
      id: 3,
      user_id: 3,
      target_type: '预约单',
      target_id: hold.id,
      content: '到现场发现座位被他人占用，请协助核实。',
      status: '处理中',
      handler_id: 5,
      handle_note: '已调取现场巡查记录，核实中。',
      handled_at: null,
      created_at: formatDateTime(addDays(now, -1)),
    },
    {
      id: 4,
      user_id: 2,
      target_type: '用户',
      target_id: 3,
      content: '有同学在静音区长时间通话。',
      status: '已驳回',
      handler_id: 5,
      handle_note: '缺少具体时间与证据，建议补充后重新提交。',
      handled_at: formatDateTime(addDays(now, -2)),
      created_at: formatDateTime(addDays(now, -4)),
    },
    {
      id: 5,
      user_id: 4,
      target_type: '座位',
      target_id: seatIdOf('G-05'),
      content: '座位积灰，请安排清洁。',
      status: '已关闭',
      handler_id: 5,
      handle_note: '与投诉 #1 为同类问题，已合并处理。',
      handled_at: formatDateTime(addDays(now, -5)),
      created_at: formatDateTime(addDays(now, -6)),
    },
    {
      // 管理端「待处理队列」的超时样本：提交已超过 3 个工作日（BR-014），用于核对超时标红
      id: 6,
      user_id: 3,
      target_type: '座位',
      target_id: seatIdOf('F-02'),
      content: '插座接触不良，换了两个座位都没电，希望尽快维修。',
      status: '待处理',
      handler_id: null,
      handle_note: null,
      handled_at: null,
      created_at: formatDateTime(addDays(now, -7)),
    },
  ]

  // ⑦ 站内消息：含未读（铃铛角标数据来源）
  const relatedReservation = studentInUse?.id ?? cancelled?.id ?? hold.id
  const messageSeeds: Array<{
    type: string
    title: string
    content: string
    relatedType: string | null
    relatedId: number | null
    isRead: boolean
    minutesAgo: number
  }> = [
    {
      type: '预约通知',
      title: '预约成功',
      content: `你已预约 ${demo.day === today ? '今日' : '明日'} ${minutesToTime(demo.start).slice(0, 5)} 的座位，请按时签到。`,
        relatedType: '预约单',
        relatedId: relatedReservation,
        isRead: true,
        minutesAgo: 48 * 60,
      },
      {
        type: '违约通知',
        title: '违约记录已登记',
        content: '你有一条预约超过签到截止时间仍未签到，已记为自动违约，累计违约将导致账户受限。',
        relatedType: '违约记录',
        relatedId: 7,
        isRead: false,
        minutesAgo: 20 * 60,
      },
      {
        type: '投诉反馈',
        title: '投诉已受理',
        content: '你提交的投诉已受理，处理时限为 3 个工作日，进度可在「我的投诉」查看。',
        relatedType: '投诉',
        relatedId: 1,
        isRead: false,
        minutesAgo: 6 * 60,
      },
      {
        type: '系统通知',
        title: '系统维护通知',
        content: '本周日 22:00–24:00 系统例行维护，期间可能无法访问，请提前安排。',
        relatedType: null,
        relatedId: null,
        isRead: true,
        minutesAgo: 5 * 24 * 60,
      },
      {
        type: '预约通知',
        title: '签到提醒',
        content: '签到窗口为预约开始前 15 分钟至开始后 15 分钟，逾期未签到将判定违约。',
        relatedType: '预约单',
        relatedId: relatedReservation,
        isRead: false,
        minutesAgo: 30,
      },
    ]

    const messages: MessageRecord[] = messageSeeds.map((seed, index) => ({
      id: index + 1,
      user_id: 1,
      type: seed.type,
      title: seed.title,
      content: seed.content,
      related_type: seed.relatedType,
      related_id: seed.relatedId,
      is_read: seed.isRead,
      created_at: formatDateTime(addMinutes(now, -seed.minutesAgo)),
    }))

// ⑧ 黑名单：1 条生效中的自动限制 + 1 条已解除的历史记录
const blacklist: BlacklistEntry[] = [
  {
    id: 1,
    user_id: 4,
    reason: '累计有效违约达到 3 次，系统自动限制 7 天',
    mode: '自动',
    start_at: formatDateTime(addDays(now, -2)),
    expire_at: formatDateTime(addDays(now, 5)),
    released_at: null,
    operator_id: null,
  },
  {
    id: 2,
    user_id: 3,
    reason: '多次占座不到场，管理员手动限制（已解除）',
    mode: '手动',
    start_at: formatDateTime(addDays(now, -20)),
    expire_at: formatDateTime(addDays(now, -13)),
    released_at: formatDateTime(addDays(now, -13)),
    operator_id: 5,
    released_reason: '当事人提交情况说明，经核实后提前解除',
    released_by: 5,
  },
]

for (const user of users) {
  user.violation_count = violations.filter((item) => item.user_id === user.id).length
}

return {
  users,
  rooms,
  areas,
  seats,
  reservations,
  violations,
  reviews,
  complaints,
  blacklist,
  messages,
  sessions: new Map(),
  attempts: [],
  armed_conflicts: 0,
}
}

/**
 * 演示用目标时段：下一个对齐 30 分钟的时段；若距闭馆不足 2 小时则顺延到次日 08:00。
 * 「A-01 已占用 [t, t+2h)，可预约 [t+2h, t+4h)」的相邻时段验证依赖该值。
 */
function demoTarget(now: Date, today: Date): { day: Date; start: number } {
  const aligned = Math.max(OPEN, ceilToStep(now, STEP))
  if (aligned + 120 > CLOSE) {
    return { day: addDays(today, 1), start: OPEN }
  }
  return { day: today, start: aligned }
}

