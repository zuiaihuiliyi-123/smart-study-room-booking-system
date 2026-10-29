/**
 * 「我的预约」页状态机（FR-030 记录查询 + FR-011 取消 + FR-020/021 签到签退 + FR-041 评价）。
 *
 * 口径来源（不要在这里发明规则）：
 * - BR-011：距开始 **≥30 分钟**才能无损取消；**不足 30 分钟时用户不能自行取消**
 *   （ST-029 提交即被拒绝），该情形**不计违约**，只能由管理员按 FR-011 强制取消。
 *   因此本页不存在「有损取消」路径：按钮直接禁用并说明原因。
 * - BR-007：签到窗口 `[s−15, s+15)`；窗口未开 / 已关闭时按钮禁用并在提示里给出窗口时间。
 * - BR-013：仅「已完成」且**尚无评价**的预约单可评价，一单一评，评分 1～5。
 *
 * 已知接口限制：`/reservations/me` 只支持 `status / page / page_size`（无日期与自习室参数），
 * 因此日期、自习室不做服务端筛选；状态页签的数量角标用 5 次 `page_size=1` 的查询取 `total`
 * （服务端计数，避免把「当前页」当成全部）。
 */
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import { cancelReservation, checkIn, checkOut, listMyReservations } from '@/api/reservation'
import { createReview, listMyReviews } from '@/api/review'
import type { Reservation } from '@/types'
import { loadSeatDirectory, toBookingFailure, type SeatRef } from '@/utils/bookingData'
import {
  BOOKING_RULES,
  bracketRangeText,
  cancelDeadlineAt,
  checkinWindow,
} from '@/utils/bookingRules'
import { parseFocusId } from '@/utils/messageLinks'
import { useClock } from '@/utils/useClock'

export interface StatusTab {
  value: string
  label: string
  /** 该页签的空态文案 */
  empty: string
}

export const STATUS_TABS: readonly StatusTab[] = [
  { value: 'all', label: '全部', empty: '还没有预约记录，去「预约座位」选一个时段吧' },
  { value: '待使用', label: '待使用', empty: '当前没有待使用的预约' },
  { value: '使用中', label: '使用中', empty: '当前没有使用中的预约' },
  { value: '已完成', label: '已完成', empty: '还没有已完成的预约' },
  { value: '已取消', label: '已取消', empty: '没有已取消的预约' },
  { value: '已违约', label: '已违约', empty: '没有违约记录，请继续保持' },
]

/** 5 种终态 / 中间态，用于取各页签的数量角标（不含「全部」）。 */
const COUNT_STATUSES: readonly Reservation['status'][] = [
  '待使用',
  '使用中',
  '已完成',
  '已取消',
  '已违约',
]

/** 行内按钮的启用条件与禁用原因：由页面统一提供，表格组件只负责渲染。 */
export interface ReservationGating {
  canCheckIn(item: Reservation): boolean
  canCancel(item: Reservation): boolean
  checkinTip(item: Reservation): string
  cancelTip(item: Reservation): string
}

/** 取本人全部评价（`/reviews/me` 同样只有分页参数）。 */
async function fetchAllMyReviews(pageSize = 100, maxPages = 5): Promise<number[]> {
  const ids: number[] = []
  for (let page = 1; page <= maxPages; page += 1) {
    const result = await listMyReviews({ page, page_size: pageSize })
    ids.push(...result.items.map((item) => item.reservation_id))
    if (result.items.length === 0 || ids.length >= result.total) break
  }
  return ids
}

export function useMyReservations() {
  const route = useRoute()
  const clock = useClock()

  const status = ref<string>('all')
  const page = ref(1)
  const pageSize = ref(10)
  const items = ref<Reservation[]>([])
  const total = ref(0)
  const counts = ref<Record<string, number>>({})
  const loading = ref(true)
  const errorMessage = ref('')
  const actingId = ref<number | null>(null)
  const reviewedIds = ref<Set<number>>(new Set())
  const directory = ref<Map<number, SeatRef> | null>(null)
  const focusId = ref<number | null>(parseFocusId(route.query.focus))

  const reviewTarget = ref<Reservation | null>(null)
  const reviewSubmitting = ref(false)

  const currentTab = computed(
    () => STATUS_TABS.find((tab) => tab.value === status.value) ?? STATUS_TABS[0],
  )

  async function loadCounts(): Promise<void> {
    const pages = await Promise.all(
      COUNT_STATUSES.map((value) => listMyReservations({ status: value, page: 1, page_size: 1 })),
    )
    const next: Record<string, number> = { all: 0 }
    COUNT_STATUSES.forEach((value, index) => {
      next[value] = pages[index].total
      next.all += pages[index].total
    })
  counts.value = next
}

async function load(): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    const result = await listMyReservations({
      status: status.value === 'all' ? undefined : status.value,
      page: page.value,
      page_size: pageSize.value,
    })
  items.value = result.items
  total.value = result.total
} catch (caught) {
  errorMessage.value = toBookingFailure(caught).message
  items.value = []
  total.value = 0
} finally {
  loading.value = false
}
if (directory.value === null) {
  directory.value = await loadSeatDirectory().catch(() => null)
}
}

/** 操作成功后刷新：数量角标与列表都要更新。 */
async function refresh(): Promise<void> {
  await Promise.all([load(), loadCounts()])
}

async function bootstrap(): Promise<void> {
  loading.value = true
  const [reviews] = await Promise.all([
    fetchAllMyReviews().catch(() => [] as number[]),
    loadCounts().catch(() => undefined),
  ])
reviewedIds.value = new Set(reviews)
await load()
}

function onTabChange(): void {
  page.value = 1
  focusId.value = null
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

/* ------------------------------------------------ 行内按钮的启用条件 */

function canCheckIn(item: Reservation): boolean {
  if (item.status !== '待使用') return false
  const window = checkinWindow(item.reserve_date, item.start_time)
  const current = clock.value.getTime()
  return current >= window.opensAt.getTime() && current < window.closesAt.getTime()
}

function checkinTip(item: Reservation): string {
  if (item.status !== '待使用') {
    return `当前状态为「${item.status}」，不能签到`
  }
  const window = checkinWindow(item.reserve_date, item.start_time)
  const current = clock.value.getTime()
  if (current < window.opensAt.getTime()) {
    return `签到窗口尚未开启：${window.opensText} 起可签到（开始前 ${BOOKING_RULES.checkinEarly} 分钟）`
  }
  if (current >= window.closesAt.getTime()) {
    return `已超过签到截止时间 ${window.closesText}（开始后 ${BOOKING_RULES.checkinLate} 分钟），该预约将判定为违约`
  }
  return `签到窗口 ${window.rangeText}（${window.opensText} 起），点击完成签到`
}

function canCancel(item: Reservation): boolean {
  if (item.status !== '待使用') return false
  const deadline = cancelDeadlineAt(item.reserve_date, item.start_time)
  if (deadline === null) return false
  return clock.value.getTime() <= deadline.getTime()
}

function cancelTip(item: Reservation): string {
  if (item.status !== '待使用') {
    return `仅「待使用」可取消，当前状态为「${item.status}」`
  }
  const deadline = cancelDeadlineAt(item.reserve_date, item.start_time)
  if (deadline === null) return '预约时间信息不完整，无法判断可取消时限'
  if (canCancel(item)) {
    return `距开始仍超过 ${BOOKING_RULES.cancelBefore} 分钟，可无损取消：不产生违约记录，该时段立即对其他同学开放`
  }
  return `距开始不足 ${BOOKING_RULES.cancelBefore} 分钟，已超过无损取消时限：用户不能自行取消，本情形不计违约；如需释放座位请联系管理员强制取消`
}

const gating: ReservationGating = { canCheckIn, canCancel, checkinTip, cancelTip }

/* ------------------------------------------------ 操作 */

async function onCheckIn(item: Reservation): Promise<void> {
  if (!canCheckIn(item)) {
    ElMessage.warning(checkinTip(item))
    return
  }
  actingId.value = item.id
  try {
    const result = await checkIn(item.id)
    ElMessage.success(result.message)
    await refresh()
  } catch {
    // 失败提示由 request.ts 拦截器统一给出（ST-027 / ST-031 的文案来自服务端）
  } finally {
    actingId.value = null
  }
}

async function onCheckOut(item: Reservation): Promise<void> {
  actingId.value = item.id
  try {
    const result = await checkOut(item.id)
    ElMessage.success(result.message)
    await refresh()
  } catch {
    // 同上
  } finally {
    actingId.value = null
  }
}

async function onCancel(item: Reservation): Promise<void> {
  if (!canCancel(item)) {
    ElMessage.warning(cancelTip(item))
    return
  }
  try {
    await ElMessageBox.confirm(
      `预约单 #${item.id}（${item.reserve_date} ${bracketRangeText(item.start_time, item.end_time)}）距开始超过 ${BOOKING_RULES.cancelBefore} 分钟，属于无损取消：不产生违约记录，该时段立即对其他同学开放。`,
      '确认取消预约',
      {
        confirmButtonText: '确认取消',
        cancelButtonText: '再想想',
        type: 'warning',
      },
    )
  } catch {
    return // 用户在确认框里点了「再想想」
  }

  actingId.value = item.id
  try {
    const result = await cancelReservation(item.id, '用户主动取消')
    ElMessage.success(result.message)
    if (items.value.length === 1 && page.value > 1) page.value -= 1
    await refresh()
  } catch {
    // 同上：如时限在页面停留期间已过，服务端会返回 CANCEL_TOO_LATE（ST-029）
  } finally {
    actingId.value = null
  }
}

/* ------------------------------------------------ 评价（FR-041 / BR-013） */

function canReview(item: Reservation): boolean {
  return item.status === '已完成' && !reviewedIds.value.has(item.id)
}

function openReview(item: Reservation): void {
  if (!canReview(item)) return
  reviewTarget.value = item
}

function closeReview(): void {
  reviewTarget.value = null
}

async function submitReview(payload: { score: number; content: string }): Promise<void> {
  const target = reviewTarget.value
  if (!target) return
  if (payload.score < 1) {
    ElMessage.warning('请先选择 1～5 星评分')
    return
  }
  reviewSubmitting.value = true
  try {
    await createReview({
      reservation_id: target.id,
      score: payload.score,
      content: payload.content.trim() || undefined,
    })
  ElMessage.success('评价已提交，感谢你的反馈')
  reviewedIds.value = new Set([...reviewedIds.value, target.id])
  closeReview()
} catch {
  // 服务端会再校验一次「已完成 + 未评价」（REVIEW_EXISTS / STATUS_NOT_ALLOWED）
} finally {
  reviewSubmitting.value = false
}
}

/* ------------------------------------------------ 站内消息跳转高亮 */

watch(
  () => route.query.focus,
  (raw) => {
    focusId.value = parseFocusId(raw)
  },
)

return {
  clock,
  status,
  page,
  pageSize,
  items,
  total,
  counts,
  loading,
  errorMessage,
  actingId,
  reviewedIds,
  directory,
  focusId,
  currentTab,
  tabs: STATUS_TABS,
  gating,
  reviewTarget,
  reviewSubmitting,
  canReview,
  bootstrap,
  load,
  refresh,
  onTabChange,
  onPageChange,
  onPageSizeChange,
  onCheckIn,
  onCheckOut,
  onCancel,
  openReview,
  closeReview,
  submitReview,
}
}

