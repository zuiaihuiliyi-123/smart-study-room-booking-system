/**
 * 「我的违约」页状态机（FR-032 违规记录查询 + FR-044 账户状态）。
 *
 * 口径来源：
 * - BR-009：累计**有效**违约次数达到 **3 次**触发限制；BR-010：限制 **7 天**后自动解除。
 * - 学生只能查本人的违约记录（BR-018），也**不得看到他人姓名与学号**（NFR-006），
 *   因此「登记人」一列对手动违约只显示操作者编号，不显示管理员姓名。
 *
 * 已知接口限制：后端没有学生可读的「限制记录」接口（`GET /blacklist` 为管理员专属，
 * `UserRead` 也没有到期时间字段），因此预计解除时间取 `CurrentUser.restrict_until`
 * （后端补齐后自动生效），缺失时页面明确标注「待后端提供接口」而不是推算一个日期。
 */
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'

import { listMyViolations } from '@/api/violation'
import { useAuthStore } from '@/stores/auth'
import type { Reservation, Violation } from '@/types'
import {
  fetchAllMyReservations,
  loadSeatDirectory,
  seatDisplayName,
  toBookingFailure,
  type SeatRef,
} from '@/utils/bookingData'
import { BOOKING_RULES, bracketRangeText, restrictUntilText } from '@/utils/bookingRules'
import { parseFocusId } from '@/utils/messageLinks'

export function useMyViolations() {
  const route = useRoute()
  const auth = useAuthStore()

  const items = ref<Violation[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(10)
  const loading = ref(true)
  const errorMessage = ref('')
  const refreshing = ref(false)
  const focusId = ref<number | null>(parseFocusId(route.query.focus))
  const directory = ref<Map<number, SeatRef> | null>(null)
  const reservations = ref<Map<number, Reservation>>(new Map())

  const threshold = BOOKING_RULES.violationThreshold
  const count = computed(() => auth.user?.violation_count ?? 0)
  const remaining = computed(() => Math.max(0, threshold - count.value))
  const percent = computed(() => Math.min(100, Math.round((count.value / threshold) * 100)))
  /** 接近阈值变色：达到阈值 → 红；差 1 次 → 黄；其余 → 绿 */
  const tone = computed<'ok' | 'warn' | 'danger'>(() => {
    if (count.value >= threshold) return 'danger'
    return count.value >= threshold - 1 ? 'warn' : 'ok'
  })
const progressStatus = computed<'success' | 'warning' | 'exception'>(() => {
  if (tone.value === 'danger') return 'exception'
  return tone.value === 'warn' ? 'warning' : 'success'
})
const accountStatus = computed(() => auth.user?.account_status ?? '—')
const restricted = computed(() => accountStatus.value === '受限')
const disabled = computed(() => accountStatus.value === '停用')
const restrictUntil = computed(() => restrictUntilText(auth.user?.restrict_until ?? ''))

function reservationLabel(reservationId: number): string {
  const record = reservations.value.get(reservationId)
  if (!record) return `预约单 #${reservationId}`
  return `#${record.id} · ${record.reserve_date} ${bracketRangeText(
  record.start_time,
  record.end_time,
)} · ${seatDisplayName(directory.value, record.seat_id)}`
  }

  /** NFR-006：不展示他人姓名，只显示操作者编号。 */
  function operatorLabel(item: Violation): string {
    return item.operator_id === null ? '系统自动判定' : `管理员 #${item.operator_id}`
  }

  async function load(): Promise<void> {
    loading.value = true
    errorMessage.value = ''
    try {
      const result = await listMyViolations({ page: page.value, page_size: pageSize.value })
      items.value = result.items
      total.value = result.total
    } catch (caught) {
      errorMessage.value = toBookingFailure(caught).message
      items.value = []
      total.value = 0
    } finally {
      loading.value = false
    }
  }

  /** 关联预约与座位目录：只为把 `reservation_id` 渲染成人能读的一行，失败可降级。 */
  async function loadContext(): Promise<void> {
    if (directory.value === null) {
      directory.value = await loadSeatDirectory().catch(() => null)
    }
    try {
      const list = await fetchAllMyReservations()
      reservations.value = new Map(list.map((item) => [item.id, item]))
    } catch {
      reservations.value = new Map()
    }
  }

  async function bootstrap(): Promise<void> {
    await Promise.all([load(), loadContext(), auth.fetchMe().catch(() => undefined)])
  }

  /** 刷新按钮：同时刷新账户状态（管理员处理违约后累计次数会变化）。 */
  async function refresh(): Promise<void> {
    refreshing.value = true
    try {
      await bootstrap()
    } finally {
      refreshing.value = false
    }
  }

  function onPageChange(next: number): void {
    page.value = next
    focusId.value = null
    void load()
  }

  function onPageSizeChange(next: number): void {
    pageSize.value = next
    page.value = 1
    void load()
  }

  return {
    items,
    total,
    page,
    pageSize,
    loading,
    refreshing,
    errorMessage,
    focusId,
    threshold,
    count,
    remaining,
    percent,
    tone,
    progressStatus,
    accountStatus,
    restricted,
    disabled,
    restrictUntil,
    reservationLabel,
    operatorLabel,
    load,
    refresh,
    bootstrap,
    onPageChange,
    onPageSizeChange,
  }
}
