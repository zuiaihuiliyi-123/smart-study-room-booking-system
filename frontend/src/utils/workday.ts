/**
 * 投诉处理时限（BR-014：**3 个工作日**）与超时判定。
 *
 * 口径说明（不自行发挥的部分）：
 * - 需求规格说明书 BR-014 只给出「3 个工作日」这一条时限，**未规定**节假日日历、
 *   是否按自然时/时刻计算，也未规定超时后的升级机制（第 7.6 节明确「提醒与升级机制
 *   属实现层，本版不规定」）。因此本文件只实现**可判定的最小口径**：
 *   跳过周六 / 周日（无法定节假日数据源），从创建时刻所在自然日的次日起算工作日，
 *   截止时刻取第 3 个工作日的 23:59（当日结束）。
 * - 「已超时天数」按**自然日**给出（人可读的迟到量），并在界面上同时标注
 *   「处理时限 3 个工作日」与精确截止时刻，避免把两种口径混为一谈。
 */
import dayjs from 'dayjs'

/** BR-014 本版取值：投诉处理时限 3 个工作日。 */
export const COMPLAINT_SLA_WORKDAYS = 3

const DAY_MS = 86_400_000

function isWeekend(day: dayjs.Dayjs): boolean {
  return day.day() === 0 || day.day() === 6
}

/** 处理时限截止时刻 = 创建时刻后的第 3 个工作日 23:59；创建时刻非法时返回 null。 */
export function complaintDeadline(
  createdAt: string | null | undefined,
  workdays: number = COMPLAINT_SLA_WORKDAYS,
): Date | null {
  const start = dayjs(createdAt)
  if (!createdAt || !start.isValid()) return null
  let cursor = start
  let counted = 0
  // 上限保护：即使 workdays 取值异常也不会无限循环
  for (let guard = 0; counted < workdays && guard < 400; guard += 1) {
    cursor = cursor.add(1, 'day')
    if (!isWeekend(cursor)) counted += 1
  }
  return cursor.endOf('day').toDate()
}

/** 从 `from` 到 `to` 之间（不含 from 当日、含 to 当日）的完整工作日数。 */
export function workdaysBetween(from: Date, to: Date): number {
  if (to.getTime() <= from.getTime()) return 0
  let cursor = dayjs(from).startOf('day')
  const end = dayjs(to).startOf('day')
  let counted = 0
  for (let guard = 0; guard < 400 && cursor.isBefore(end); guard += 1) {
    cursor = cursor.add(1, 'day')
    if (!isWeekend(cursor)) counted += 1
  }
  return counted
}

export interface ComplaintSla {
  /** 截止时刻；创建时间缺失或非法时为 null，此时界面不展示时限结论 */
  deadline: Date | null
  /** `YYYY-MM-DD HH:mm` */
  deadlineText: string
  /** 是否已超过处理时限 */
  overdue: boolean
  /** 已超时的自然日数（向上取整，未超时恒为 0） */
  overdueDays: number
  /** 距截止尚余的工作日数（已超时恒为 0） */
  remainingWorkdays: number
  /** 时限口径说明，界面直接展示 */
  note: string
}

/** 一次算出界面需要的全部时限结论，避免各页面各自推算（口径只在本文件维护）。 */
export function complaintSla(
  createdAt: string | null | undefined,
  now: Date,
  workdays: number = COMPLAINT_SLA_WORKDAYS,
): ComplaintSla {
  const deadline = complaintDeadline(createdAt, workdays)
  const note = `处理时限 ${workdays} 个工作日（跳过周六 / 周日；法定节假日无数据源，本版不计算）`
  if (deadline === null) {
    return { deadline: null, deadlineText: '—', overdue: false, overdueDays: 0, remainingWorkdays: 0, note }
  }
  const overdue = now.getTime() > deadline.getTime()
  return {
    deadline,
    deadlineText: dayjs(deadline).format('YYYY-MM-DD HH:mm'),
    overdue,
    overdueDays: overdue ? Math.max(1, Math.ceil((now.getTime() - deadline.getTime()) / DAY_MS)) : 0,
    remainingWorkdays: overdue ? 0 : workdaysBetween(now, deadline),
    note,
  }
}
