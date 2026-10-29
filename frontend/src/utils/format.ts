import dayjs from 'dayjs'

/**
 * 全站日期时间格式化的唯一出口（AGENTS.md §3：视图与组件不直接依赖 dayjs）。
 *
 * 约定：
 * - 空值一律返回占位符（默认 `-`），由调用方决定是否换成 `—` 或「未记录」；
 * - 后端时间字符串可能是 `YYYY-MM-DDTHH:mm:ss` 或带时区，统一交给 dayjs 解析；
 * - **只做展示格式化**。业务口径（例如「哪些状态算有效预约」）不放在这里。
 */

type DateInput = string | number | Date | null | undefined

function parse(value: DateInput): dayjs.Dayjs | null {
  if (value === null || value === undefined || value === '') return null
  const parsed = dayjs(value)
  return parsed.isValid() ? parsed : null
}

/** `YYYY-MM-DD HH:mm`（列表/详情默认格式） */
export function formatDateTime(value: DateInput): string {
  return parse(value)?.format('YYYY-MM-DD HH:mm') ?? '-'
}

/** `YYYY-MM-DD` */
export function formatDate(value: DateInput): string {
  return parse(value)?.format('YYYY-MM-DD') ?? '-'
}

/** `HH:mm:ss`（看板「数据截至时间」这类只关心当天时刻的场合） */
export function formatTimeSecond(value: DateInput): string {
  return parse(value)?.format('HH:mm:ss') ?? '-'
}

/** `MM-DD HH:mm`（列表里省略年份，完整时间见详情抽屉） */
export function formatMonthDayTime(value: DateInput): string {
  return parse(value)?.format('MM-DD HH:mm') ?? '-'
}

/** `MM-DD`（折线图横轴等紧凑场合） */
export function formatMonthDay(value: DateInput): string {
  return parse(value)?.format('MM-DD') ?? '-'
}

/** `YYYY-MM-DDTHH:mm:ss`：提交给后端的时间字段（与 mock 的 `formatDateTime` 同构） */
export function formatApiDateTime(value: DateInput): string {
  return parse(value)?.format('YYYY-MM-DDTHH:mm:ss') ?? ''
}

/** 近 N 天区间（含今天），返回 `[start, end]`，用于看板与筛选区默认值 */
export function recentRange(days: number): [string, string] {
  const end = dayjs()
  return [end.subtract(days - 1, 'day').format('YYYY-MM-DD'), end.format('YYYY-MM-DD')]
}

/** 是否晚于今天（用于日期选择器的 `disabled-date`：不许选未来） */
export function isAfterToday(value: Date): boolean {
  return dayjs(value).isAfter(dayjs().endOf('day'))
}

/** 是否早于今天（用于日期选择器的 `disabled-date`：不许选过去） */
export function isBeforeToday(value: Date): boolean {
  return dayjs(value).isBefore(dayjs().startOf('day'))
}
