import type { AuditLog } from '@/types'
import {
  reservationLabelOf,
  roomNameOf,
  seatIdLabel,
  userLabelOf,
  type AdminDirectory,
} from '@/utils/adminData'

export const ACTION_OPTIONS: { value: string; label: string }[] = [
  { value: 'LOGIN_SUCCESS', label: '登录成功' },
  { value: 'LOGIN_FAILED', label: '登录失败' },
  { value: 'LOGIN_LOCKED', label: '登录锁定' },
  { value: 'REGISTER_SUCCESS', label: '注册成功' },
  { value: 'PASSWORD_CHANGED', label: '修改密码' },
  { value: 'UNAUTHORIZED_ATTEMPT', label: '越权尝试' },
  { value: 'ACCOUNT_STATUS_UPDATE', label: '账户状态变更' },
  { value: 'BLACKLIST_ADD', label: '加入黑名单' },
  { value: 'BLACKLIST_RELEASE', label: '解除黑名单' },
  { value: 'BLACKLIST_AUTO_RESTRICT', label: '自动限制' },
  { value: 'MANUAL_VIOLATION', label: '手动违约登记' },
  { value: 'RESERVATION_FORCE_CANCEL', label: '强制取消预约' },
  { value: 'ROOM_UPDATE', label: '修改自习室' },
  { value: 'ROOM_DELETE', label: '删除自习室' },
  { value: 'ROOM_TEMP_CLOSE', label: '临时关闭' },
  { value: 'ROOM_CLOSURE_RELEASE', label: '解除临时关闭' },
  { value: 'SEAT_STATUS_UPDATE', label: '修改座位状态' },
  { value: 'SEAT_STATUS_BATCH', label: '批量修改座位状态' },
  { value: 'COMPLAINT_HANDLE', label: '处理投诉' },
  { value: 'COMPLAINT_CONFIRM', label: '确认关闭投诉' },
]

export const TARGET_OPTIONS: { value: string; label: string }[] = [
  { value: 'USER', label: '用户' },
  { value: 'SEAT', label: '座位' },
  { value: 'ROOM', label: '自习室' },
  { value: 'reservation', label: '预约单' },
  { value: 'COMPLAINT', label: '投诉' },
  { value: 'api', label: '接口' },
]

const ACTION_LABELS = new Map(ACTION_OPTIONS.map((item) => [item.value, item.label]))
const TARGET_LABELS = new Map(TARGET_OPTIONS.map((item) => [item.value, item.label]))

export function actionLabel(value: string): string {
  return ACTION_LABELS.get(value) ?? value
}

export function targetLabel(directory: AdminDirectory | null, row: AuditLog): string {
  const id = row.target_id
  const type = TARGET_LABELS.get(row.target_type) ?? row.target_type
  if (id === null) return type
  if (row.target_type === 'USER') return userLabelOf(directory, id)
  if (row.target_type === 'SEAT') return seatIdLabel(directory, id)
  if (row.target_type === 'ROOM') return roomNameOf(directory, id)
  if (row.target_type === 'reservation') return reservationLabelOf(directory, id)
  return `${type} #${id}`
}

export function hasChange(row: AuditLog): boolean {
  return Boolean(row.before_value || row.after_value)
}

export function prettyValue(value: string | null): string {
  if (!value) return '—'
  try {
    return JSON.stringify(JSON.parse(value), null, 2)
  } catch {
    return value
  }
}
