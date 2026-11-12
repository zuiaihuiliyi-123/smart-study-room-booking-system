/**
 * 开发期 Mock 的「服务器时间」与时间序列化工具。
 *
 * 业务代码只读真实时间；偏移量仅存在于 mock 层（内存 + localStorage），
 * 用于演示签到窗口、自动违约等与时间强相关的分支。
 * 生产构建不会包含本文件（见 main.ts 的动态 import 条件）。
 */

const OFFSET_KEY = 'ssr_mock_time_offset_minutes'
const MINUTE_MS = 60_000
const DAY_MS = 86_400_000

function readStoredOffset(): number {
  try {
    const raw = localStorage.getItem(OFFSET_KEY)
    if (raw === null) return 0
    const parsed = Number.parseInt(raw, 10)
    return Number.isFinite(parsed) ? parsed : 0
  } catch {
    return 0
  }
}

let offsetMinutes = readStoredOffset()

export function getTimeOffsetMinutes(): number {
  return offsetMinutes
}

/** 设置服务器时间偏移（分钟，可为负），返回生效后的偏移值。 */
export function setTimeOffsetMinutes(minutes: number): number {
  const next = Number.isFinite(minutes) ? Math.trunc(minutes) : 0
  offsetMinutes = next
  try {
    if (next === 0) localStorage.removeItem(OFFSET_KEY)
    else localStorage.setItem(OFFSET_KEY, String(next))
  } catch {
    // 隐私模式等场景下持久化失败不影响本次会话
  }
  return offsetMinutes
}

/** 当前「服务器时间」= 真实时间 + 偏移。 */
export function serverNow(): Date {
  return new Date(Date.now() + offsetMinutes * MINUTE_MS)
}

export function pad2(value: number): string {
  return String(value).padStart(2, '0')
}

/** 本地时区的 YYYY-MM-DD（与后端 date 序列化一致）。 */
export function formatDate(value: Date): string {
  return `${value.getFullYear()}-${pad2(value.getMonth() + 1)}-${pad2(value.getDate())}`
}

/** 本地时区的 HH:MM:SS（与后端 time 序列化一致）。 */
export function formatTime(value: Date): string {
  return `${pad2(value.getHours())}:${pad2(value.getMinutes())}:${pad2(value.getSeconds())}`
}

/** 本地时区的 YYYY-MM-DDTHH:mm:ss（与后端 naive datetime 序列化一致）。 */
export function formatDateTime(value: Date): string {
  return `${formatDate(value)}T${formatTime(value)}`
}

/** 把后端 datetime 字符串展示为 YYYY-MM-DD HH:mm。 */
export function readableDateTime(value: string | null): string {
  if (!value) return '-'
  return value.replace('T', ' ').slice(0, 16)
}

export function startOfDay(value: Date): Date {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate())
}

export function addDays(value: Date, days: number): Date {
  const next = new Date(value)
  next.setDate(next.getDate() + days)
  return next
}

export function addMinutes(value: Date, minutes: number): Date {
  return new Date(value.getTime() + minutes * MINUTE_MS)
}

/** 自然日差值（按日历日计算，忽略时分秒）。 */
export function dayDiff(from: Date, to: Date): number {
  return Math.round((startOfDay(to).getTime() - startOfDay(from).getTime()) / DAY_MS)
}

/** 分钟数（自 00:00 起）→ "HH:MM:SS"。 */
export function minutesToTime(minutes: number): string {
  return `${pad2(Math.floor(minutes / 60))}:${pad2(minutes % 60)}:00`
}

/** "HH:MM" 或 "HH:MM:SS" → 分钟数；格式非法返回 null。 */
export function parseTimeMinutes(value: string): number | null {
  const matched = /^(\d{1,2}):(\d{2})(?::(\d{2}))?$/.exec(value.trim())
  if (!matched) return null
  const hours = Number(matched[1])
  const minute = Number(matched[2])
  const second = matched[3] === undefined ? 0 : Number(matched[3])
  if (hours > 23 || minute > 59 || second > 59) return null
  return hours * 60 + minute
}

/** "YYYY-MM-DD" → 当天 00:00；格式非法返回 null。 */
export function parseDate(value: string): Date | null {
  const matched = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value.trim())
  if (!matched) return null
  const parsed = new Date(Number(matched[1]), Number(matched[2]) - 1, Number(matched[3]))
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export function combine(day: Date, minutes: number): Date {
  return new Date(
    day.getFullYear(),
    day.getMonth(),
    day.getDate(),
    Math.floor(minutes / 60),
    minutes % 60,
    0,
    0,
  )
}

export function minutesOfDay(value: Date): number {
  return value.getHours() * 60 + value.getMinutes()
}

export function floorToStep(value: Date, stepMinutes: number): number {
  const minutes = minutesOfDay(value)
  return minutes - (minutes % stepMinutes)
}

export function ceilToStep(value: Date, stepMinutes: number): number {
  const minutes = minutesOfDay(value)
  const remainder = minutes % stepMinutes
  return remainder === 0 ? minutes : minutes + (stepMinutes - remainder)
}

/** 左闭右开区间重叠判定（BR-020）：s1 < e2 且 s2 < e1。 */
export function overlaps(aStart: number, aEnd: number, bStart: number, bEnd: number): boolean {
  return aStart < bEnd && bStart < aEnd
}
