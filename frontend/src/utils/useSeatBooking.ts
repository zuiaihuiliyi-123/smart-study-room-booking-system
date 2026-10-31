/**
 * 预约座位页的状态机与取数（FR-013 查询 → FR-012 校验 → FR-010 创建）。
 *
 * 关键约定：
 * - 幂等键（BR-021）按「座位 + 日期 + 时段」这一个预约意图生成一次，并缓存在意图表里：
 *   关闭抽屉再打开同一意图会复用同一个键（重试即幂等，返回同一张预约单），
 *   换成另一个座位 / 时段才生成新键（新意图）。提交按钮点击时不会重新生成键。
 * - 筛选条件与已选座位都保存在本 composable 内，改筛选、查询失败都不会清空已选。
 * - 时间判定以服务端为准（NFR-010）；此处的「已开始」「提前天数」等只是提交前的本地预估。
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { createReservation } from '@/api/reservation'
import { listRooms } from '@/api/room'
import type { BookingFilters, MatrixGroup, SubmitState, SubmitSuccess } from '@/components/booking/types'
import { useAuthStore } from '@/stores/auth'
import type { Reservation, Room, Seat } from '@/types'
import {
  defaultSlotForDate,
  groupSeatsByArea,
  loadSlotAvailability,
  toBookingFailure,
} from '@/utils/bookingData'
import type { BookingFailure, JudgementItem } from '@/utils/bookingRules'
import {
  BOOKING_RULES,
  buildJudgements,
  ceilToStep,
  checkinWindow,
  dayOffsetFromToday,
  minutesToTimeText,
  mySlotUsage,
  occupancyText,
  parseTimeToMinutes,
  restrictUntilText,
  seatCellState,
  shortTime,
  timeRangeText,
  todayIso,
  userBlockReason,
} from '@/utils/bookingRules'
import { bookingDateOptions } from '@/utils/bookingRules'
import { useClock } from '@/utils/useClock'

const EMPTY_IDS: ReadonlySet<number> = new Set<number>()

function fallbackKey(): string {
  const bytes = new Uint8Array(16)
  globalThis.crypto?.getRandomValues?.(bytes)
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
}

/** 幂等键：优先 crypto.randomUUID()（BR-021 要求 8～64 位）。 */
export function createIdempotencyKey(): string {
  const uuid = globalThis.crypto?.randomUUID?.()
  return uuid ?? fallbackKey()
}

export function useSeatBooking() {
  const clock = useClock()
  const auth = useAuthStore()

  const rooms = ref<Room[]>([])
  const seats = ref<Seat[]>([])
  const myReservations = ref<Reservation[]>([])
  const availableIds = ref<ReadonlySet<number> | null>(null)
  const loading = ref(true)
  const loadError = ref<BookingFailure | null>(null)

  const filters = reactive<BookingFilters>({
    roomId: null,
    reserveDate: '',
    startTime: '',
    endTime: '',
    seatType: '',
    powerOnly: false,
  })

const selectedSeatId = ref<number | null>(null)
const drawerVisible = ref(false)
const currentKey = ref('')
const submitState = ref<SubmitState>('idle')
const failure = ref<BookingFailure | null>(null)
const success = ref<SubmitSuccess | null>(null)
/** 本次会话已成功的提交，按意图键缓存，重新打开同一意图时仍显示「已提交」 */
const submitted = ref(new Map<string, SubmitSuccess>())
const intentKeys = new Map<string, string>()

/* ---------------------------------------------------------------- 派生量 */

const todayKey = computed(() => todayIso(clock.value))
const minuteTick = computed(() => Math.floor(clock.value.getTime() / 60_000))
const dateOptions = computed(() => bookingDateOptions(new Date(`${todayKey.value}T00:00:00`)))
const room = computed(() => rooms.value.find((item) => item.id === filters.roomId) ?? null)
const openTime = computed(() => shortTime(room.value?.open_time) || '08:00')
const closeTime = computed(() => shortTime(room.value?.close_time) || '22:00')
const seatTypes = computed(() => [...new Set(seats.value.map((seat) => seat.seat_type))])

/** 今天的最早可选开始时间；已过去的时刻不可选（服务端同样拒绝，见 TIME_STARTED）。 */
const minStartTime = computed(() => {
  void minuteTick.value
  const open = parseTimeToMinutes(openTime.value) ?? 8 * 60
  const close = parseTimeToMinutes(closeTime.value) ?? 22 * 60
  if (filters.reserveDate !== todayKey.value) return minutesToTimeText(open)
  const now = clock.value
  const aligned = ceilToStep(Math.max(open, now.getHours() * 60 + now.getMinutes()))
  return minutesToTimeText(Math.min(aligned, close))
})

const usage = computed(() =>
    mySlotUsage(myReservations.value, filters.reserveDate, filters.startTime, filters.endTime),
)
const userBlock = computed(() => userBlockReason(usage.value))

const visibleSeats = computed(() =>
    seats.value.filter(
    (seat) =>
      (filters.seatType === '' || seat.seat_type === filters.seatType) &&
      (!filters.powerOnly || seat.has_power),
  ),
)

const groups = computed<MatrixGroup[]>(() => {
  const ids = availableIds.value
  if (ids === null) return []
  return groupSeatsByArea(visibleSeats.value).map((group) => ({
    key: group.key,
    title: group.title,
    note: group.note,
    cells: group.seats.map((seat) => ({
      seat,
      state: seatCellState(seat, ids),
      occupancy: occupancyText(seat, ids),
    })),
}))
})

const freeCount = computed(() => {
  const ids = availableIds.value
  if (ids === null) return 0
  return visibleSeats.value.filter((seat) => seatCellState(seat, ids) === 'free').length
})

const selectedSeat = computed(
  () => seats.value.find((seat) => seat.id === selectedSeatId.value) ?? null,
)

const selectedAreaTitle = computed(() => {
  const hit = groups.value.find((group) =>
      group.cells.some((cell) => cell.seat.id === selectedSeatId.value),
  )
  return hit?.title ?? '—'
})

const staleReason = computed(() =>
    selectedSeatId.value !== null && selectedSeat.value === null
    ? '已选座位不属于当前筛选的自习室，请重新选择后再提交。'
    : '',
)

const judgements = computed<JudgementItem[]>(() => {
  const seat = selectedSeat.value
  const currentRoom = room.value
  if (!seat || !currentRoom) return []
  return buildJudgements({
    seat,
    room: currentRoom,
    reserveDate: filters.reserveDate,
    startTime: filters.startTime,
    endTime: filters.endTime,
    availableIds: availableIds.value,
    usage: usage.value,
    accountStatus: auth.user?.account_status ?? '正常',
    restrictUntil: restrictUntilText(
      failure.value?.restrictUntil || auth.user?.restrict_until || '',
    ),
    dayOffset: dayOffsetFromToday(clock.value, filters.reserveDate),
  })
})

const canSubmit = computed(
  () =>
    submitState.value === 'idle' &&
    selectedSeat.value !== null &&
    staleReason.value === '' &&
    judgements.value.length > 0 &&
    judgements.value.every((item) => item.state === 'pass'),
)

const summary = computed(() => {
  const label =
    dateOptions.value.find((item) => item.value === filters.reserveDate)?.label ??
    filters.reserveDate
  return `${room.value?.name ?? '—'} · ${label} · ${timeRangeText(filters.startTime, filters.endTime)}`
})

const hint = computed(() => {
  if (loadError.value) return ''
  if (userBlock.value) return '该时段没有可预约座位'
  return `可约 ${freeCount.value} / ${visibleSeats.value.length} 座`
})

const blockedHint = computed(() => {
  const block = userBlock.value
  if (block === null) return ''
  if (block === 'C4') {
    const conflict = usage.value.conflict
    return `时段冲突：你在 ${filters.reserveDate} ${timeRangeText(
  conflict?.start_time ?? '',
  conflict?.end_time ?? '',
)} 已有有效预约（预约单 #${conflict?.id ?? '-'}）。同一用户在同一时段不得存在两条有效预约，因此该时段没有可预约座位。`
    }
    return `每日次数已达上限：你在 ${filters.reserveDate} 已有 ${usage.value.dailyCount} 条有效预约，达到每人每日 ${BOOKING_RULES.dailyLimit} 条上限，当日不能再预约。`
  })

/* ---------------------------------------------------------------- 取数 */

/**
 * 默认时段：在「按日期取默认时段」的基础上，顺延跳过本人已有的有效预约（C4），
 * 否则「重置」会把用户带回一个必然撞上自己的时段，只能看到「该时段不可预约」。
 */
function defaultSlotAvoidingSelf(): { startTime: string; endTime: string } {
  const close = parseTimeToMinutes(closeTime.value) ?? 22 * 60
  let slot = defaultSlotForDate(room.value, filters.reserveDate, clock.value)
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const mine = mySlotUsage(
      myReservations.value,
      filters.reserveDate,
      slot.startTime,
      slot.endTime,
    )
    const conflictEnd = mine.conflict ? parseTimeToMinutes(mine.conflict.end_time) : null
    if (conflictEnd === null || conflictEnd + 60 > close) break
    slot = {
      startTime: minutesToTimeText(conflictEnd),
      endTime: minutesToTimeText(Math.min(conflictEnd + 120, close)),
    }
  }
  return slot
}

function applyDefaults() {
  const first = rooms.value[0] ?? null
  filters.roomId = first?.id ?? null
  filters.reserveDate = todayIso(clock.value)
  const slot = defaultSlotAvoidingSelf()
  filters.startTime = slot.startTime
  filters.endTime = slot.endTime
  filters.seatType = ''
  filters.powerOnly = false
}

function validationError(): string | null {
  if (filters.roomId === null) return '请先选择自习室'
  if (!filters.reserveDate) return '请选择预约日期'
  const start = parseTimeToMinutes(filters.startTime)
  const end = parseTimeToMinutes(filters.endTime)
  if (start === null || end === null) return '请选择开始时间与结束时间'
  if (end <= start) return '结束时间必须晚于开始时间'
  if (end - start > BOOKING_RULES.maxHours * 60) {
    return `单次预约时长不能超过 ${BOOKING_RULES.maxHours} 小时`
  }
  if (start % BOOKING_RULES.granularity !== 0 || end % BOOKING_RULES.granularity !== 0) {
    return `预约时间须以 ${BOOKING_RULES.granularity} 分钟为粒度，须对齐整点或半点`
  }
  const offset = dayOffsetFromToday(clock.value, filters.reserveDate)
  if (offset < 0) return '不能预约已经过去的日期'
  if (offset > BOOKING_RULES.advanceDays) {
    return `最多只能提前 ${BOOKING_RULES.advanceDays} 天预约`
  }
  if (offset === 0) {
    const now = clock.value
    if (start <= now.getHours() * 60 + now.getMinutes()) {
      return '该时段已经开始，不能预约，请改选后面的时段'
    }
  }
  return null
}

/**
 * 校验不通过时**不再发请求**，但要保证界面不卡在「正在查询…」：
 * 之前只弹一条会消失的 toast，`loading` 留在 true，页面就永远转圈（收口轮修掉）。
 * 这里把原因同时写进 `loadError`，让错误块常驻显示，并提供重试入口。
 */
async function query() {
  const problem = validationError()
  if (problem) {
    loading.value = false
    loadError.value = {
      kind: 'rule',
      message: problem,
      judgement: null,
      code: 'INVALID_SLOT',
      rule: '',
      restrictUntil: '',
    }
    ElMessage.warning(problem)
    return
  }
  if (filters.roomId === null) {
    loading.value = false
    return
  }
  loading.value = true
  loadError.value = null
  try {
    const data = await loadSlotAvailability(
      filters.roomId,
      filters.reserveDate,
      filters.startTime,
      filters.endTime,
    )
    seats.value = data.seats
    availableIds.value = data.availableIds
    myReservations.value = data.myReservations
  } catch (error) {
    // 失败不清空已选条件：filters 与 selectedSeatId 保持原值
    availableIds.value = null
    loadError.value = toBookingFailure(error)
  } finally {
    loading.value = false
  }
}

async function bootstrap() {
  try {
    rooms.value = await listRooms()
  } catch (error) {
    loadError.value = toBookingFailure(error)
    loading.value = false
    return
  }
  applyDefaults()
  await query()
  // 首屏默认时段若与本人既有有效预约重叠（C4），自动顺延到冲突结束之后，
  // 否则用户一进页面就只看到「该时段不可预约」而看不到座位矩阵。
  if (userBlock.value === 'C4') {
    await findAlternative()
    ElMessage.info('默认时段与你现有的有效预约重叠，已自动改选到冲突结束后的时段')
  }
}

function resetFilters() {
  applyDefaults()
  void query()
}

/** 换自习室后把时段收进新馆的开放时间，避免留下必然失败的组合。 */
function applyRoomChange() {
  const open = parseTimeToMinutes(openTime.value) ?? 8 * 60
  const close = parseTimeToMinutes(closeTime.value) ?? 22 * 60
  const start = parseTimeToMinutes(filters.startTime)
  const end = parseTimeToMinutes(filters.endTime)
  if (start === null || end === null || start < open || end > close || end <= start) {
    const slot = defaultSlotAvoidingSelf()
    filters.startTime = slot.startTime
    filters.endTime = slot.endTime
  }
}

/** 换回今天时若原时段已过，自动收敛到下一个可预约时段。 */
function applyDateChange() {
  if (filters.reserveDate !== todayKey.value) return
  const now = clock.value
  const start = parseTimeToMinutes(filters.startTime)
  if (start !== null && start <= now.getHours() * 60 + now.getMinutes()) {
    const slot = defaultSlotAvoidingSelf()
    filters.startTime = slot.startTime
    filters.endTime = slot.endTime
  }
}

/* ---------------------------------------------------------------- 提交意图 */

function intentCombo(): string {
  return [selectedSeatId.value ?? 0, filters.reserveDate, filters.startTime, filters.endTime].join('|')
}

/** 同一意图只生成一次幂等键；重试沿用原键（幂等），换座位 / 时段才换键。 */
function syncIntent() {
  const combo = intentCombo()
  if (!intentKeys.has(combo)) intentKeys.set(combo, createIdempotencyKey())
  currentKey.value = intentKeys.get(combo) ?? ''
  const done = submitted.value.get(combo) ?? null
  success.value = done
  submitState.value = done ? 'submitted' : 'idle'
  if (!done) failure.value = null
}

function openSeat(seat: Seat) {
  selectedSeatId.value = seat.id
  syncIntent()
  drawerVisible.value = true
}

async function submit() {
  const seat = selectedSeat.value
  if (!seat || submitState.value !== 'idle') return
  submitState.value = 'submitting'
  failure.value = null
  try {
    const created = await createReservation({
      seat_id: seat.id,
      reserve_date: filters.reserveDate,
      start_time: filters.startTime,
      end_time: filters.endTime,
      idempotency_key: currentKey.value,
    })
  const info: SubmitSuccess = {
    id: created.id,
    seatText: `${room.value?.name ?? ''} · ${seat.seat_no}`,
    reserveDate: created.reserve_date,
    startTime: created.start_time,
    endTime: created.end_time,
    window: checkinWindow(created.reserve_date, created.start_time),
  }
  submitted.value.set(intentCombo(), info)
  success.value = info
  submitState.value = 'submitted'
  ElMessage.success('预约提交成功')
  // 刷新可预约座位：该座位该时段按 C3 变为不可预约，同时本人当日次数 +1
  await query()
} catch (error) {
  failure.value = toBookingFailure(error)
  submitState.value = 'idle'
}
}

/** 只要「本人时段占用 / 每日次数」这类用户级条件成立，界面就不再显示座位矩阵。 */
async function findAlternative() {
  const conflict = usage.value.conflict
  if (userBlock.value === 'C4' && conflict) {
    const close = parseTimeToMinutes(closeTime.value) ?? 22 * 60
    const start = parseTimeToMinutes(conflict.end_time) ?? 0
    if (start + 60 <= close) {
      filters.startTime = minutesToTimeText(start)
      filters.endTime = minutesToTimeText(Math.min(start + 120, close))
      await query()
      return
    }
  }
  const options = dateOptions.value
  const index = options.findIndex((item) => item.value === filters.reserveDate)
  const next = options[Math.min(index + 1, options.length - 1)]
  if (next && next.value !== filters.reserveDate) filters.reserveDate = next.value
  const slot = defaultSlotAvoidingSelf()
  filters.startTime = slot.startTime
  filters.endTime = slot.endTime
  await query()
}

watch(
  () => [selectedSeatId.value, filters.reserveDate, filters.startTime, filters.endTime].join('|'),
  () => {
    if (drawerVisible.value) syncIntent()
  },
)

onMounted(() => {
  // 刷新账户状态，保证 C5（用户资格）用的是服务端当前值
  void auth.fetchMe().catch(() => undefined)
  void bootstrap()
})

return {
  // 数据
  rooms,
  seats,
  filters,
  loading,
  loadError,
  // 派生
  dateOptions,
  room,
  openTime,
  closeTime,
  seatTypes,
  minStartTime,
  groups,
  freeCount,
  visibleCount: computed(() => visibleSeats.value.length),
  userBlock,
  blockedHint,
  summary,
  hint,
  // 抽屉
  drawerVisible,
  selectedSeat,
  selectedSeatId,
  selectedAreaTitle,
  staleReason,
  judgements,
  canSubmit,
  submitState,
  failure,
  success,
  // 行为
  query,
  resetFilters,
  applyRoomChange,
  applyDateChange,
  openSeat,
  submit,
  findAlternative,
  availableEmpty: computed(() => availableIds.value !== null && freeCount.value === 0),
  emptyIds: EMPTY_IDS,
}
}

