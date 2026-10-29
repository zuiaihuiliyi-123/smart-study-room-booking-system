/**
 * 「座位管理」页状态机（FR-003 / FR-004 / FR-031 / BR-017 / BR-019 / BR-022）。
 *
 * 两个维度严格分开（AGENTS.md §4）：
 * - **资源状态**：可用 / 维修中 / 停用，来自 `seat.status`，由管理员通过 FR-004 调整；
 * - **时段占用**：某座位在「选定日期 + 时段」是否已存在有效预约，由 `/seats/occupancy` 实时计算，
 *   只作为展示与筛选条件，**永远不写回座位状态**。
 *
 * 冲突处理（BR-019）：座位转「维修中 / 停用」前先列出冲突的有效预约，**只提示、不自动取消**；
 * 影响面超过一条时按 BR-022 要求二次确认。
 */
import { computed, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

import { listSeatConflicts, listSeatOccupancy, updateSeatStatusBatch } from '@/api/seat'
import type { MatrixCell } from '@/components/booking/types'
import type { Reservation, Seat, SeatOccupancy } from '@/types'
import {
  areaLabelOf,
  invalidateAdminDirectory,
  loadAdminDirectory,
  type AdminDirectory,
} from '@/utils/adminData'
import {
  defaultBookingSlot,
  groupSeatsByArea,
  toBookingFailure,
  type SeatGroupData,
} from '@/utils/bookingData'
import {
  occupancyText,
  seatCellState,
  type SeatCellState,
} from '@/utils/bookingRules'
import { useAdminScope } from '@/utils/useAdminScope'

export type SeatStatusFilter = '全部' | '可用' | '维修中' | '停用'
export type OccupancyFilter = '全部' | '可约' | '已被预约'
export type SeatView = 'grid' | 'list'

export interface SeatGridGroup {
  key: string
  title: string
  note: string
  cells: MatrixCell[]
}

const SEAT_STATUSES: readonly Seat['status'][] = ['可用', '维修中', '停用']

export function useSeatManage() {
  const scope = useAdminScope()
  const now = new Date()

  const roomId = ref<number | null>(null)
  const areaId = ref<'all' | number>('all')
  const statusFilter = ref<SeatStatusFilter>('全部')
  const occupancyFilter = ref<OccupancyFilter>('全部')
  const view = ref<SeatView>('grid')

  const reserveDate = ref(dayjs(now).format('YYYY-MM-DD'))
  const startTime = ref('08:00')
  const endTime = ref('10:00')

  const directory = ref<AdminDirectory | null>(null)
  const items = ref<SeatOccupancy[]>([])
  const loading = ref(true)
  const refreshing = ref(false)
  const errorMessage = ref('')
  const occupancyNote = ref('')

  const page = ref(1)
  const pageSize = ref(20)
  const selectedIds = ref<number[]>([])

  const statusDrawerVisible = ref(false)
  const targetStatus = ref<Seat['status']>('维修中')
  const reason = ref('')
  const conflictFrom = ref(`${dayjs(now).format('YYYY-MM-DD')}T08:00`)
  const conflictTo = ref(`${dayjs(now).add(6, 'day').format('YYYY-MM-DD')}T22:00`)
  const conflicts = ref<Reservation[]>([])
  const conflictsQueried = ref(false)
  const conflictLoading = ref(false)
  const conflictError = ref('')
  const executing = ref(false)

  const rooms = scope.rooms

  const timeError = computed(() => {
    if (startTime.value === '' || endTime.value === '') return '请选择查询时段'
    return endTime.value > startTime.value ? '' : '结束时刻必须晚于开始时刻（区间为左闭右开 [s, e)）'
  })

const windowStart = computed(() => `${reserveDate.value}T${startTime.value}`)
const windowEnd = computed(() => `${reserveDate.value}T${endTime.value}`)

/** 该时段可约的座位 id 集合：资源状态「可用」且无占用 */
const availableIds = computed(
  () =>
    new Set(
    items.value
      .filter((item) => item.seat.status === '可用' && !item.occupied)
      .map((item) => item.seat.id),
  ),
)

const filtered = computed(() =>
    items.value.filter(({ seat, occupied }) => {
    if (areaId.value !== 'all' && seat.area_id !== areaId.value) return false
    if (statusFilter.value !== '全部' && seat.status !== statusFilter.value) return false
    if (occupancyFilter.value === '可约' && (seat.status !== '可用' || occupied)) return false
    if (occupancyFilter.value === '已被预约' && !occupied) return false
    return true
  }),
)

const total = computed(() => filtered.value.length)
const paged = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})

const areaOptions = computed(() => {
  if (directory.value === null || roomId.value === null) return []
  const named = directory.value.areasByRoom.get(roomId.value)
  if (named && named.length > 0) return named
  const seats = directory.value.seatsByRoom.get(roomId.value) ?? []
  const ids = [
      ...new Set(seats.map((seat) => seat.area_id).filter((id): id is number => id !== null)),
  ]
  return ids.map((id) => ({
    id,
    room_id: roomId.value ?? 0,
    name: areaLabelOf(directory.value, id, seats),
  }))
})

const gridGroups = computed<SeatGridGroup[]>(() => {
  const groups: SeatGroupData[] = groupSeatsByArea(filtered.value.map((item) => item.seat))
  const bySeat = new Map(items.value.map((item) => [item.seat.id, item]))
  return groups.map((group) => ({
    key: group.key,
    // 管理端能拿到分区名（座位目录）时优先用真实名称：`分区 A` 只是后端缺 `GET /areas` 时的兜底
    title:
    group.key === 'unassigned'
      ? group.title
      : areaLabelOf(directory.value, Number(group.key), group.seats),
    note: group.note,
    cells: group.seats.map((seat) => {
      const hit = bySeat.get(seat.id)
      const state: SeatCellState = seatCellState(seat, availableIds.value)
      return {
        seat,
        state,
        occupancy: hit ? occupancyText(seat, availableIds.value) : '未判定',
      }
    }),
}))
})

const selectedSeats = computed(() =>
    items.value.map((item) => item.seat).filter((seat) => selectedIds.value.includes(seat.id)),
)


async function load(force = false): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  occupancyNote.value = ''
  try {
    if (force) invalidateAdminDirectory()
    await scope.ensureLoaded(force)
    if (roomId.value === null && rooms.value.length > 0) {
      roomId.value = rooms.value[0]?.id ?? null
    }
    if (directory.value === null || force) {
      directory.value = await loadAdminDirectory(force).catch(() => null)
    }
    if (roomId.value === null) {
      items.value = []
      return
    }
    if (timeError.value !== '') {
      // 时段非法时不发请求：只保留资源状态，明确标注占用「未判定」，不猜测
      occupancyNote.value = `${timeError.value}；当前仅展示资源状态，时段占用未判定。`
      items.value = (directory.value?.seatsByRoom.get(roomId.value) ?? []).map((seat) => ({
        seat,
        occupied: false,
        reservation: null,
      }))
  return
}
items.value = await listSeatOccupancy({
  room_id: roomId.value,
  reserve_date: reserveDate.value,
  start_time: startTime.value,
  end_time: endTime.value,
})
const ids = new Set(items.value.map((item) => item.seat.id))
selectedIds.value = selectedIds.value.filter((id) => ids.has(id))
} catch (caught) {
  errorMessage.value = toBookingFailure(caught).message
  items.value = []
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
  areaId.value = 'all'
  statusFilter.value = '全部'
  occupancyFilter.value = '全部'
  const room = rooms.value.find((item) => item.id === roomId.value) ?? null
  const slot = defaultBookingSlot(room, new Date())
  startTime.value = slot.startTime
  endTime.value = slot.endTime
  reserveDate.value = dayjs().format('YYYY-MM-DD')
  selectedIds.value = []
  page.value = 1
  void load()
}

function onRoomChange(): void {
  areaId.value = 'all'
  selectedIds.value = []
  page.value = 1
  const room = rooms.value.find((item) => item.id === roomId.value) ?? null
  const slot = defaultBookingSlot(room, new Date())
  startTime.value = slot.startTime
  endTime.value = slot.endTime
  void load()
}

function onPageChange(next: number): void {
  page.value = next
}

function toggleSeat(seat: Seat): void {
  const index = selectedIds.value.indexOf(seat.id)
  if (index >= 0) selectedIds.value.splice(index, 1)
  else selectedIds.value.push(seat.id)
}

function selectGroup(cells: readonly MatrixCell[]): void {
  const ids = cells.map((cell) => cell.seat.id)
  const allSelected = ids.every((id) => selectedIds.value.includes(id))
  selectedIds.value = allSelected
    ? selectedIds.value.filter((id) => !ids.includes(id))
    : [...new Set([...selectedIds.value, ...ids])]
}

function clearSelection(): void {
  selectedIds.value = []
}

function openStatusDrawer(seat?: Seat): void {
  if (seat) {
    if (!scope.guardSeat(seat)) return
    selectedIds.value = [seat.id]
  }
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先选择要调整的座位（列表视图可多选，网格视图可点选或按分区全选）')
    return
  }
  for (const item of selectedSeats.value) {
    if (!scope.guardSeat(item)) return
  }
  targetStatus.value = selectedSeats.value.every((item) => item.status === '可用')
    ? '维修中'
    : '可用'
  reason.value = ''
  conflicts.value = []
  conflictsQueried.value = false
  conflictError.value = ''
  const today = dayjs().format('YYYY-MM-DD')
  conflictFrom.value = `${today}T08:00`
  conflictTo.value = `${dayjs().add(6, 'day').format('YYYY-MM-DD')}T22:00`
  statusDrawerVisible.value = true
}

/** BR-019 第一步：查询冲突的有效预约（只读） */
async function checkConflicts(): Promise<void> {
  if (selectedIds.value.length === 0) return
  if (conflictTo.value <= conflictFrom.value) {
    ElMessage.warning('调整窗口不合法：结束时刻必须晚于开始时刻')
    return
  }
  conflictLoading.value = true
  conflictError.value = ''
  try {
    conflicts.value = await listSeatConflicts({
      seat_ids: selectedIds.value,
      start_at: conflictFrom.value,
      end_at: conflictTo.value,
    })
  conflictsQueried.value = true
} catch (caught) {
  conflictError.value = toBookingFailure(caught).message
  conflicts.value = []
} finally {
  conflictLoading.value = false
}
}

/** FR-004 + BR-022：批量调整资源状态（先列冲突 → 二次确认 → 执行） */
async function executeStatusChange(): Promise<void> {
  if (selectedIds.value.length === 0) return
  if (!SEAT_STATUSES.includes(targetStatus.value)) {
    ElMessage.warning('目标状态只能是「可用 / 维修中 / 停用」')
    return
  }
  if (reason.value.trim() === '') {
    ElMessage.warning('请填写调整原因：原因会写入审计日志')
    return
  }

  const count = selectedIds.value.length
  const impact =
    conflictsQueried.value && conflicts.value.length > 0
    ? `已列出 ${conflicts.value.length} 条冲突的有效预约：系统只作提示，不会自动取消。`
    : conflictsQueried.value
    ? '该窗口内没有冲突的有效预约。'
    : '你还没有查询冲突清单（要求先列清单再决定）。'

  try {
    await ElMessageBox.confirm(
      `将 ${count} 个座位的资源状态调整为「${targetStatus.value}」${count > 1 ? '（批量操作）' : ''}。${impact}本次操作将记入审计日志，确认执行？`,
      count > 1 ? '二次确认：批量调整座位状态' : '确认：调整座位资源状态',
      { type: 'warning', confirmButtonText: '确认执行', cancelButtonText: '返回检查' },
    )
  } catch {
    return
  }

  executing.value = true
  try {
    const result = await updateSeatStatusBatch({
      seat_ids: selectedIds.value,
      status: targetStatus.value,
      reason: reason.value.trim(),
    })
  const extra =
    result.conflicts.length > 0
    ? `；服务端复核到 ${result.conflicts.length} 条冲突预约，已保留原状态并持续提示`
    : ''
  ElMessage.success(`已更新 ${result.updated.length} 个座位的资源状态${extra}`)
  invalidateAdminDirectory()
  directory.value = null
  statusDrawerVisible.value = false
  selectedIds.value = []
  await load(true)
} catch (caught) {
  ElMessage.error(toBookingFailure(caught).message)
} finally {
  executing.value = false
}
}

return {
  scopeLabel: scope.scopeLabel,
  rooms,
  roomId,
  areaId,
  statusFilter,
  occupancyFilter,
  view,
  reserveDate,
  startTime,
  endTime,
  directory,
  items,
  loading,
  refreshing,
  errorMessage,
  occupancyNote,
  page,
  pageSize,
  total,
  paged,
  selectedIds,
  selectedSeats,
  availableIds,
  areaOptions,
  gridGroups,
  timeError,
  windowStart,
  windowEnd,
  statusDrawerVisible,
  targetStatus,
  reason,
  conflictFrom,
  conflictTo,
  conflicts,
  conflictsQueried,
  conflictLoading,
  conflictError,
  executing,
  load,
  refresh,
  onSearch,
  onReset,
  onRoomChange,
  onPageChange,
  toggleSeat,
  selectGroup,
  clearSelection,
  openStatusDrawer,
  checkConflicts,
  executeStatusChange,
}
}

