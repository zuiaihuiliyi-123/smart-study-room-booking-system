/**
 * 「投诉处理」页状态机（FR-043 + BR-014）。
 *
 * 队列口径：默认进入「待处理」队列（管理员的实际工作队列），可切换到其它状态或全部；
 * 另可按对象类型、提交时间区间筛选。
 *
 * 状态流转严格照第 5.4 节状态转换表（ST-060～ST-063）：
 * - 待处理 → 处理中（受理，ST-060）；
 * - 待处理 → 已驳回（必填驳回理由，ST-061）；
 * - 处理中 → 已处理（必填处理说明，ST-062）；
 * - 已处理 → 已关闭由**投诉人确认 / 系统超时**触发（ST-063），管理端不提供该入口。
 *
 * BR-014 时限：自提交起 3 个工作日应给出处理结果；超时以站内提示实现、**不设自动升级**。
 * 本页把「已超时天数」直接标在行上（界面层补充，不改变任何业务规则）。
 */
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { handleComplaint, listAllComplaints } from '@/api/complaint'
import type { Complaint } from '@/types'
import {
  complaintTargetLabel,
  invalidateAdminDirectory,
  loadAdminDirectory,
  type AdminDirectory,
} from '@/utils/adminData'
import { toBookingFailure } from '@/utils/bookingData'
import { useAdminScope } from '@/utils/useAdminScope'
import { useClock } from '@/utils/useClock'
import { COMPLAINT_SLA_WORKDAYS, complaintSla } from '@/utils/workday'

export type ComplaintStatusFilter = '待处理' | '处理中' | '已处理' | '已驳回' | '已关闭' | '全部'
export type ComplaintTargetFilter = '全部' | '座位' | '自习室' | '预约单' | '用户'

export function useComplaintManage() {
  const scope = useAdminScope()
  /** 每分钟刷新一次超时判定（BR-014 的截止时刻是 3 个工作日后的 23:59，无需秒级精度） */
  const now = useClock(60_000)

  const directory = ref<AdminDirectory | null>(null)
  const items = ref<Complaint[]>([])
  const total = ref(0)
  const loading = ref(true)
  const refreshing = ref(false)
  const errorMessage = ref('')

  /** 默认「待处理」队列（FR-043 的实际工作入口） */
  const statusFilter = ref<ComplaintStatusFilter>('待处理')
  const targetFilter = ref<ComplaintTargetFilter>('全部')
  const dateRange = ref<string[]>([])
  const page = ref(1)
  const pageSize = ref(20)

  const detailVisible = ref(false)
  const detail = ref<Complaint | null>(null)
  const submitting = ref(false)

  const overdueCount = computed(
    () => items.value.filter((item) => complaintSla(item.created_at, now.value).overdue).length,
  )

  async function load(force = false): Promise<void> {
    loading.value = true
    errorMessage.value = ''
    try {
      if (force) invalidateAdminDirectory()
      const [result, dir] = await Promise.all([
        listAllComplaints({
          page: page.value,
          page_size: pageSize.value,
          status: statusFilter.value === '全部' ? undefined : statusFilter.value,
          target_type: targetFilter.value === '全部' ? undefined : targetFilter.value,
          created_from: dateRange.value[0],
          created_to: dateRange.value[1],
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
  statusFilter.value = '待处理'
  targetFilter.value = '全部'
  dateRange.value = []
  page.value = 1
  void load()
}

function onPageChange(next: number): void {
  page.value = next
  void load()
}

function onPageSizeChange(next: number): void {
  pageSize.value = next
  page.value = 1
  void load()
}

/** 当前投诉可执行的下一步（严格照 ST-060～ST-063，界面据此决定显示哪些按钮） */
function nextActions(item: Complaint | null): Complaint['status'][] {
  if (item === null) return []
  if (item.status === '待处理') return ['处理中', '已驳回']
  if (item.status === '处理中') return ['已处理']
  return []
}

function openDetail(item: Complaint): void {
  detail.value = item
  detailVisible.value = true
}

async function submitHandle(status: Complaint['status'], note: string): Promise<boolean> {
  const target = detail.value
  if (target === null) return false
  if (!nextActions(target).includes(status)) {
    ElMessage.warning(`「${target.status}」不能流转到「${status}」（～）`)
    return false
  }
  if (note.trim() === '') {
    ElMessage.warning('处理说明 / 驳回理由必填：该内容会同步给投诉人并记入审计日志')
    return false
  }
  const actionText =
    status === '已驳回'
    ? '驳回该投诉'
    : status === '处理中'
    ? '受理该投诉并转为「处理中」'
    : '录入处理结果并转为「已处理」'
  try {
    await ElMessageBox.confirm(
      `将投诉 #${target.id}（${complaintTargetLabel(directory.value, target.target_type, target.target_id)}）${actionText}。处理说明会同步给投诉人，本次操作将记入审计日志。确认提交？`,
      '确认：投诉处理（～）',
      { type: 'warning', confirmButtonText: '确认提交', cancelButtonText: '返回修改' },
    )
  } catch {
    return false
  }
  submitting.value = true
  try {
    const updated = await handleComplaint(target.id, { status, handle_note: note.trim() })
    ElMessage.success(`投诉 #${updated.id} 已流转为「${updated.status}」`)
    invalidateAdminDirectory()
    await refresh()
    // 流转后该投诉通常会离开当前筛选队列（默认只看「待处理」），仍保留这条最新快照，
    // 否则抽屉会在关闭瞬间变成空白；若还有下一步（如 处理中 → 已处理），可直接继续处理。
    detail.value = updated
    return true
  } catch (caught) {
    ElMessage.error(toBookingFailure(caught).message)
    return false
  } finally {
    submitting.value = false
  }
}

function targetText(item: Complaint): string {
  return complaintTargetLabel(directory.value, item.target_type, item.target_id)
}

function slaOf(item: Complaint): ReturnType<typeof complaintSla> {
  return complaintSla(item.created_at, now.value)
}

return {
  scopeLabel: scope.scopeLabel,
  directory,
  items,
  total,
  loading,
  refreshing,
  errorMessage,
  statusFilter,
  targetFilter,
  dateRange,
  page,
  pageSize,
  detailVisible,
  detail,
  submitting,
  overdueCount,
  slaWorkdays: COMPLAINT_SLA_WORKDAYS,
  load,
  refresh,
  onSearch,
  onReset,
  onPageChange,
  onPageSizeChange,
  openDetail,
  submitHandle,
  nextActions,
  targetText,
  slaOf,
}
}
