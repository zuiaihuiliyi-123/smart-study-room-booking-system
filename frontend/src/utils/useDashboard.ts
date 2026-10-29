/**
 * 数据看板状态机（FR-050～FR-053 / NFR-001 / BR-016）。
 *
 * 本轮任务对 10 秒刷新的 5 条硬要求，逐条落在本文件里：
 * 1. **卸载清定时器**：`onBeforeUnmount` 里 `stopTimer()` + 移除 `visibilitychange` 监听；
 * 2. **防重入**：`inFlight` 守住，上一次没回来就跳过本次，并把倒计时留在 0 不再叠加请求；
 * 3. **可见性暂停 / 恢复立即拉一次**：`visibilitychange` 隐藏时停表，恢复时重置倒计时并立刻 `refresh('resume')`；
 * 4. **失败保留旧数据**：`catch` 里只记录 `lastFailedAt`，不碰 `overview / seatUsage / trend`，
 *    界面据此显示「更新失败，显示 mm:ss 的数据」；
 * 5. **增量更新**：数据以 ref 覆盖，图表由 BaseChart 用 `replaceMerge` 合并，不重建实例、不丢滚动位置。
 *
 * 口径提示：10 秒是**数据读取周期**，不是违约判定周期（后者由后端扫描任务决定，≤1 分钟）。
 * 因此页面必须标注「数据截至时间」，避免把 10 秒前读到的数据误认为实时数据。
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import { getOverview, getSeatUsageBySlot, getTrend } from '@/api/dashboard'
import { listAllViolations } from '@/api/violation'
import type { SeatUsageSlotRow, StatOverview, TrendPoint, ViolationTopEntry } from '@/types'
import { loadAdminDirectory, type AdminDirectory } from '@/utils/adminData'
import { toBookingFailure } from '@/utils/bookingData'
import { recentRange } from '@/utils/format'
import { useAdminScope } from '@/utils/useAdminScope'

/** BR-016 / NFR-001：10 秒一次数据读取（唯一有原文来源的量化指标） */
export const REFRESH_INTERVAL_MS = 10_000
const COUNTDOWN_SECONDS = REFRESH_INTERVAL_MS / 1000
/** 图 3 取前 N 名 */
export const TOP_N = 8
const VIOLATION_PAGE_SIZE = 200
const MAX_VIOLATION_PAGES = 5

export type RefreshSource = 'initial' | 'auto' | 'manual' | 'resume'

export function useDashboard() {
  const scope = useAdminScope()
  const directory = ref<AdminDirectory | null>(null)

  /* ---------- 筛选（IR-004 输入：统计周期 + 自习室） ---------- */
  /** 默认近 7 天（含今天） */
  const dateRange = ref<[string, string]>(recentRange(7))
  const roomId = ref<number | 'all'>('all')

  const query = computed(() => ({
    start_date: dateRange.value[0],
    end_date: dateRange.value[1],
      ...(roomId.value === 'all' ? {} : { room_id: roomId.value as number }),
  }))

/* ---------- 数据 ---------- */
const overview = ref<StatOverview | null>(null)
const seatUsage = ref<SeatUsageSlotRow[]>([])
const trend = ref<TrendPoint[]>([])
const topViolators = ref<ViolationTopEntry[]>([])
const violationSample = ref(0)
const violationsTruncated = ref(false)

/* ---------- 刷新状态 ---------- */
const loading = ref(true)
const inFlight = ref(false)
const errorMessage = ref('')
const lastUpdatedAt = ref<Date | null>(null)
const lastFailedAt = ref<Date | null>(null)
const refreshCount = ref(0)
const countdown = ref(COUNTDOWN_SECONDS)
const paused = ref(false)

/** 有过一次成功数据后再次失败 → 保留旧数据并提示（IR-004：不得以 0 值代替故障） */
const staleSince = computed(() => (lastFailedAt.value !== null ? lastUpdatedAt.value : null))
const hasData = computed(() => overview.value !== null)

const roomOptions = computed(() => scope.rooms.value.map((room) => ({ id: room.id, name: room.name })))

/**
 * FR-052 的 5 张卡片的视图模型。
 *
 * 放在这里而不是页面里，一是页面要守 300 行上限，二是这 5 项的口径说明必须和
 * 「数据从哪个字段来」写在同一处，避免文案与字段脱节。
 */
const cardItems = computed(() => {
  const value = overview.value
  return [
    {
      key: 'seat_total',
      label: '座位总数',
      unit: '个',
      hint: '可用座位（不含维修中 / 停用）',
      count: value?.seat_total ?? 0,
      tone: 'primary' as const,
    },
    {
      key: 'in_use',
      label: '使用中预约',
      unit: '单',
      hint: '当前「使用中」的预约单，不是座位状态',
      count: value?.in_use ?? 0,
      tone: 'success' as const,
    },
    {
      key: 'today_reservations',
      label: '今日预约',
      unit: '单',
      hint: '当日创建且未取消的预约单',
      count: value?.today_reservations ?? 0,
      tone: 'primary' as const,
    },
    {
      key: 'today_violations',
      label: '今日违约',
      unit: '条',
      hint: '当日违约记录（自动 + 手动）',
      count: value?.today_violations ?? 0,
      tone: 'danger' as const,
    },
    {
      key: 'restricted_accounts',
      label: '受限账户',
      unit: '人',
      hint: '「受限」账户数；账户不归属自习室，为全局口径',
      count: value?.restricted_accounts ?? 0,
      tone: 'warning' as const,
    },
  ]
})

/* ---------- 数据读取 ---------- */
let requestSeq = 0
/** 恢复可见时若正好有请求在飞，不硬塞第二个请求，等它回来后再补一次（见 finally） */
let pendingResume = false

/**
 * 图 3 的数据源：后端没有"用户违约次数 Top N"接口，因此从 `/violations` 明细聚合。
 * 说明写进页面（本轮任务要求标注数据来源），并记录样本量，避免让人误以为是后端聚合值。
 */
async function loadTopViolators(
  params: { start_date: string; end_date: string },
  dir: AdminDirectory | null,
): Promise<{ items: ViolationTopEntry[]; sample: number; truncated: boolean }> {
  const counters = new Map<number, number>()
  let sample = 0
  let truncated = false

  for (let page = 1; page <= MAX_VIOLATION_PAGES; page += 1) {
    const result = await listAllViolations({
      created_from: params.start_date,
      created_to: params.end_date,
      page,
      page_size: VIOLATION_PAGE_SIZE,
    })
  sample = result.total
  for (const record of result.items) {
    counters.set(record.user_id, (counters.get(record.user_id) ?? 0) + 1)
  }
  if (page * VIOLATION_PAGE_SIZE >= result.total) break
  if (page === MAX_VIOLATION_PAGES) truncated = true
}

const items = [...counters.entries()]
  .map(([userId, count]) => ({
  user_id: userId,
  name: dir?.usersById.get(userId)?.name ?? `用户 #${userId}`,
  student_no: dir?.usersById.get(userId)?.student_no ?? `#${userId}`,
  count,
}))
  .sort((left, right) => right.count - left.count || left.user_id - right.user_id)
  .slice(0, TOP_N)

return { items, sample, truncated }
}

async function refresh(source: RefreshSource = 'manual'): Promise<void> {
  // 防重入：上一次还没回来就跳过本次（任务要求），不叠加请求
  if (inFlight.value) return
  inFlight.value = true
  const seq = (requestSeq += 1)
  const params = query.value
  if (source === 'initial' || source === 'manual') {
    loading.value = !hasData.value
  }

  try {
    const [dir, nextOverview, nextUsage, nextTrend] = await Promise.all([
      loadAdminDirectory().catch(() => null),
      getOverview(params, { silent: true }),
      getSeatUsageBySlot(params, { silent: true }),
      getTrend(params, { silent: true }),
    ])
  const nextTop = await loadTopViolators(params, dir)

  // 等待期间用户改了筛选 → 丢弃这次结果，避免旧范围覆盖新范围
  if (seq !== requestSeq) return

  directory.value = dir
  overview.value = nextOverview
  seatUsage.value = nextUsage
  trend.value = nextTrend
  topViolators.value = nextTop.items
  violationSample.value = nextTop.sample
  violationsTruncated.value = nextTop.truncated
  lastUpdatedAt.value = new Date()
  lastFailedAt.value = null
  errorMessage.value = ''
  if (source === 'auto') refreshCount.value += 1
  countdown.value = COUNTDOWN_SECONDS
} catch (caught) {
  if (seq !== requestSeq) return
  // 失败**不清空**已有数据：只记下失败时刻，界面显示"更新失败，显示 mm:ss 的数据"
  lastFailedAt.value = new Date()
  if (!hasData.value) errorMessage.value = toBookingFailure(caught).message
} finally {
  if (seq === requestSeq) {
    inFlight.value = false
    loading.value = false
    // 恢复可见时被防重入挡掉的那次读取，在这里补上（保证「切回立即拉一次」）
    if (pendingResume) {
      pendingResume = false
      countdown.value = COUNTDOWN_SECONDS
      void refresh('resume')
    }
  }
}
}

/* ---------- 10 秒心跳 ---------- */
let timer: number | null = null

function startTimer(): void {
  if (timer !== null) return
  timer = window.setInterval(() => {
    if (paused.value || inFlight.value) return
    countdown.value -= 1
    if (countdown.value > 0) return
    countdown.value = COUNTDOWN_SECONDS
    void refresh('auto')
  }, 1000)
}

function stopTimer(): void {
  if (timer !== null) {
    window.clearInterval(timer)
    timer = null
  }
}

/**
 * 页面隐藏时暂停、恢复时立即拉一次。
 * 后台标签页仍每秒触发定时器会白白消耗请求配额，也让倒计时失去意义。
 */
function handleVisibility(): void {
  const hidden = document.visibilityState === 'hidden'
  paused.value = hidden
  if (hidden) {
    stopTimer()
    return
  }
  countdown.value = COUNTDOWN_SECONDS
  startTimer()
  // 正在读取时不叠第二个请求（防重入），等它回来再补一次
  if (inFlight.value) {
    pendingResume = true
  } else {
    void refresh('resume')
  }
}

/* ---------- 对外操作 ---------- */
function refreshNow(): void {
  countdown.value = COUNTDOWN_SECONDS
  void refresh('manual')
}

/** 改筛选：立刻按新范围读一次，并把倒计时重置（否则可能在 1 秒后又跳一次） */
function applyFilters(): void {
  countdown.value = COUNTDOWN_SECONDS
  void refresh('manual')
}

function resetFilters(): void {
  dateRange.value = recentRange(7)
  roomId.value = 'all'
  applyFilters()
}

onMounted(() => {
  document.addEventListener('visibilitychange', handleVisibility)
  startTimer()
  void refresh('initial')
  void scope.ensureLoaded()
})

onBeforeUnmount(() => {
  stopTimer()
  document.removeEventListener('visibilitychange', handleVisibility)
})

return {
  scopeLabel: scope.scopeLabel,
  roomOptions,
  cardItems,
  dateRange,
  roomId,
  query,
  overview,
  seatUsage,
  trend,
  topViolators,
  violationSample,
  violationsTruncated,
  directory,
  loading,
  inFlight,
  errorMessage,
  lastUpdatedAt,
  lastFailedAt,
  staleSince,
  hasData,
  refreshCount,
  countdown,
  paused,
  refreshNow,
  applyFilters,
  resetFilters,
}
}



