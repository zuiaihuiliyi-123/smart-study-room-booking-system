/**
 * 「预约管理」页状态机（FR-030 全量查询 / FR-011 强制取消 / FR-023 手动违约登记）。
 *
 * FR-011 与 FR-023 的适用边界（AGENTS.md §4、BR-015，两者**互斥**）：
 * - 强制取消：仅「待使用」（未开始）；必填原因；**不产生**违约记录、**不累加**违约次数；
 * - 手动违约登记：仅「使用中」（已签到未签退/超时）；必填原因；**会累加**违约次数，
 *   累计达到 3 次按 BR-009 / BR-010 触发 7 天限制。
 * 同一预约单不得同时出现两个可用按钮——本文件用 `canForceCancel` / `canRegisterViolation`
 * 这一对互斥判定集中控制，页面只读这两个计算结果。
 */
import { computed, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

import { forceCancelReservation, getReservation, listAllReservations } from '@/api/reservation'
import { registerManualViolation } from '@/api/violation'
import type { Reservation } from '@/types'
import {
  invalidateAdminDirectory,
  loadAdminDirectory,
  seatIdLabel,
  type AdminDirectory,
} from '@/utils/adminData'
import { bracketRangeText, durationText, slotMinutes } from '@/utils/bookingRules'
import { toBookingFailure } from '@/utils/bookingData'
import { useAdminScope } from '@/utils/useAdminScope'

export type ReservationStatusFilter =
  | '全部'
  | '待使用'
  | '使用中'
  | '已完成'
  | '已取消'
  | '已违约'

export function useReservationManage() {
  const scope = useAdminScope()

  const directory = ref<AdminDirectory | null>(null)
  const items = ref<Reservation[]>([])
  const total = ref(0)
  const loading = ref(true)
  const refreshing = ref(false)
  const errorMessage = ref('')

  const dateRange = ref<string[]>([])
  const roomId = ref<number | null>(null)
  const statusFilter = ref<ReservationStatusFilter>('全部')
  const studentNo = ref('')
  const page = ref(1)
  const pageSize = ref(20)

  const detailVisible = ref(false)
  const detail = ref<Reservation | null>(null)
  const detailLoading = ref(false)
  const detailError = ref('')

  /** 互斥判定：两个操作各自只在一个状态上可用，绝不同时可用（BR-015） */
  const canForceCancel = computed(() => detail.value?.status === '待使用')
  const canRegisterViolation = computed(() => detail.value?.status === '使用中')

  const detailUserViolations = computed(() => {
    if (detail.value === null || directory.value === null) return null
    const owner = directory.value.usersById.get(detail.value.user_id)
    return owner ? owner.violation_count : null
  })

async function load(force = false): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    if (force) invalidateAdminDirectory()
    const [result, dir] = await Promise.all([
      listAllReservations({
        page: page.value,
        page_size: pageSize.value,
        status: statusFilter.value === '全部' ? undefined : statusFilter.value,
        reserve_date_from: dateRange.value[0],
        reserve_date_to: dateRange.value[1],
        room_id: roomId.value ?? undefined,
        student_no: studentNo.value.trim() === '' ? undefined : studentNo.value.trim(),
      }),
    loadAdminDirectory(force).catch(() => null),
  ])
items.value = result.items
total.value = result.total
directory.value = dir
if (items.value.length === 0 && page.value > 1) {
  page.value -= 1
  await load()
}
void scope.ensureLoaded(force)
} catch (caught) {
  errorMessage.value = toBookingFailure(caught).message
  items.value = []
  total.value = 0
} finally {
  loading.value = false
}
}

async function refresh(): Promise<void> {
  refreshing.value = true
  try {
    await load(true)
  } finally {
    refreshing.value = false
  }
}

function onSearch(): void {
  page.value = 1
  void load()
}

function onReset(): void {
  dateRange.value = []
  roomId.value = null
  statusFilter.value = '全部'
  studentNo.value = ''
  page.value = 1
  void load()
}

function onPageChange(next: number): void {
  page.value = next
}

function onPageSizeChange(next: number): void {
  pageSize.value = next
  page.value = 1
  void load()
}

async function openDetail(item: Reservation): Promise<void> {
  detailVisible.value = true
  detail.value = item
  detailLoading.value = true
  detailError.value = ''
  try {
    // 详情以服务端为准：状态可能在列表加载后已被其他操作改变（例如用户本人签到）
    detail.value = await getReservation(item.id)
  } catch (caught) {
    detailError.value = toBookingFailure(caught).message
  } finally {
    detailLoading.value = false
  }
}

/** FR-011：管理员强制取消（仅「待使用」，不计违约、不累加次数） */
async function forceCancel(reason: string): Promise<boolean> {
  const target = detail.value
  if (target === null) return false
  if (!canForceCancel.value) {
    ElMessage.warning('强制取消仅适用于「待使用」的预约')
    return false
  }
  if (reason.trim() === '') {
    ElMessage.warning('请填写取消原因：原因会写入审计日志')
    return false
  }
  try {
    await ElMessageBox.confirm(
      `将强制取消预约 #${target.id}（${seatIdLabel(directory.value, target.seat_id)}，${target.reserve_date} ${bracketRangeText(target.start_time, target.end_time)}）。该操作不产生违约记录、不累加违约次数。本次操作将记入审计日志，确认继续？`,
      '确认：强制取消预约',
      { type: 'warning', confirmButtonText: '确认强制取消', cancelButtonText: '返回检查' },
    )
  } catch {
    return false
  }
  try {
    const result = await forceCancelReservation(target.id, reason.trim())
    ElMessage.success(`${result.message}（不产生违约记录、不累加违约次数）`)
    invalidateAdminDirectory()
    await refresh()
    detail.value = items.value.find((item) => item.id === target.id) ?? null
    if (detail.value === null) detailVisible.value = false
    return true
  } catch (caught) {
    ElMessage.error(toBookingFailure(caught).message)
    return false
  }
}

/** FR-023：管理员手动违约登记（仅「使用中」，会累加违约次数） */
async function registerViolation(reason: string): Promise<boolean> {
  const target = detail.value
  if (target === null) return false
  if (!canRegisterViolation.value) {
    ElMessage.warning('手动违约登记仅适用于「使用中」的预约')
    return false
  }
  if (reason.trim() === '') {
    ElMessage.warning('请填写登记原因：原因会写入审计日志')
    return false
  }
  const count = detailUserViolations.value
  const countText = count === null ? '' : `（当前 ${count} 次）`
  try {
    await ElMessageBox.confirm(
      `将为预约 #${target.id}（${seatIdLabel(directory.value, target.seat_id)}，${target.reserve_date} ${bracketRangeText(target.start_time, target.end_time)}）登记手动违约。该操作会累加该用户的违约次数${countText}，累计达到 3 次将限制账户 7 天。本次操作将记入审计日志，确认继续？`,
      '确认：手动违约登记',
      { type: 'warning', confirmButtonText: '确认登记违约', cancelButtonText: '返回检查' },
    )
  } catch {
    return false
  }
  try {
    const violation = await registerManualViolation({
      reservation_id: target.id,
      reason: reason.trim(),
    })
  // 登记后把「后果」直接说清楚：管理员刚把次数推到阈值时必须知道账户已被限制
  const nextCount = count === null ? null : count + 1
  const thresholdNote =
    nextCount === null
    ? '该用户的累计违约次数已累加，达到 3 次将限制账户 7 天'
    : nextCount >= 3
    ? `该用户累计违约已达 ${nextCount} 次，系统将限制账户 7 天`
    : `该用户累计违约 ${nextCount} 次（达到 3 次将限制账户 7 天）`
  ElMessage.success(`已登记手动违约（违约记录 #${violation.id}）：${thresholdNote}`)
  invalidateAdminDirectory()
  await refresh()
  detail.value = items.value.find((item) => item.id === target.id) ?? null
  if (detail.value === null) detailVisible.value = false
  return true
} catch (caught) {
  ElMessage.error(toBookingFailure(caught).message)
  return false
}
}

function slotText(item: Reservation): string {
  return `${item.reserve_date} ${bracketRangeText(item.start_time, item.end_time)}（${durationText(slotMinutes(item.start_time, item.end_time))}）`
}

/** 列表里只显示签到 / 签退时刻（同一预约单只涉及一天），完整时间在详情抽屉里 */
function clockText(value: string | null): string {
  if (value === null) return '-'
  return value.replace('T', ' ').slice(11, 16)
}

/** 日期区间只作查询范围：允许过去区间（便于查历史），未来最多到一年后 */
function disabledDate(value: Date): boolean {
  return dayjs(value).isAfter(dayjs().add(1, 'year'))
}

function operatorText(item: Reservation): string {
  if (item.cancel_reason === null) return '—'
  if (item.cancel_reason.startsWith('管理员强制取消')) {
    return `${item.cancel_reason}（管理员操作，不计违约）`
  }
  return item.cancel_reason
}

return {
  scopeLabel: scope.scopeLabel,
  rooms: scope.rooms,
  directory,
  items,
  total,
  loading,
  refreshing,
  errorMessage,
  dateRange,
  roomId,
  statusFilter,
  studentNo,
  page,
  pageSize,
  detailVisible,
  detail,
  detailLoading,
  detailError,
  canForceCancel,
  canRegisterViolation,
  detailUserViolations,
  load,
  refresh,
  onSearch,
  onReset,
  onPageChange,
  onPageSizeChange,
  openDetail,
  forceCancel,
  registerViolation,
  slotText,
  operatorText,
  clockText,
  disabledDate,
}
}
