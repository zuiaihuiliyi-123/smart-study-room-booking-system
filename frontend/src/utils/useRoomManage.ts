/**
 * 「自习室管理」页状态机（FR-001 / FR-002 / FR-016）。
 *
 * 口径来源：
 * - FR-001：新增 / 修改 / 停用自习室及其分区，维护名称、位置、开放时间与容量；
 *   本版不提供物理删除（Q-032：以「停用」代替删除，保留历史关联）。
 * - FR-002 + BR-022：批量停用须先列影响清单、二次确认（见 `RoomCloseDrawer.vue`）。
 * - NFR-009：所有写操作都要求填写原因并提示「本次操作将记入审计日志」。
 *
 * 已知口径缺口（不在本文件自行裁定，已登记到问题清单）：
 * `Room.enabled` 未被第 4.4.2 节的 C1 判定引用——即「停用自习室」目前不会让它的座位
 * 变成不可预约。因此界面把两种语义分开呈现：`启用状态`只改自习室自身标记；
 * 要立即阻止其座位被预约，须走「临时关闭」（会把范围内座位置为「停用」）。
 */
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { createRoom, listRooms, updateRoom } from '@/api/room'
import type { Room } from '@/types'
import { invalidateSeatDirectory, toBookingFailure } from '@/utils/bookingData'
import {
  areaCountOfRoom,
  invalidateAdminDirectory,
  loadAdminDirectory,
  seatCountOfRoom,
  type AdminDirectory,
} from '@/utils/adminData'
import { useAdminScope } from '@/utils/useAdminScope'

export type EnabledFilter = '全部' | '启用' | '停用'

export interface RoomFormPayload {
  name: string
  location: string
  open_time: string
  close_time: string
  capacity: number
  enabled: boolean
  /** 审计事由（NFR-009） */
  reason: string
}

export function useRoomManage() {
  const scope = useAdminScope()

  const rooms = ref<Room[]>([])
  const directory = ref<AdminDirectory | null>(null)
  const loading = ref(true)
  const refreshing = ref(false)
  const errorMessage = ref('')

  const keyword = ref('')
  const enabledFilter = ref<EnabledFilter>('全部')
  const page = ref(1)
  const pageSize = ref(10)

  const formVisible = ref(false)
  const editing = ref<Room | null>(null)
  const submitting = ref(false)
  const areaVisible = ref(false)
  const closeVisible = ref(false)
  const activeRoom = ref<Room | null>(null)

  const filtered = computed(() => {
    const text = keyword.value.trim().toLowerCase()
    return rooms.value.filter((room) => {
      if (
        text !== '' &&
          !room.name.toLowerCase().includes(text) &&
          !room.location.toLowerCase().includes(text)
      ) {
        return false
      }
      if (enabledFilter.value === '启用' && !room.enabled) return false
      if (enabledFilter.value === '停用' && room.enabled) return false
      return true
    })
})

const total = computed(() => filtered.value.length)
const paged = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})

/** 目录失败不阻塞主列表：容量 / 座位数 / 分区数按「—」展示 */
const directoryFailed = ref(false)

async function load(force = false): Promise<void> {
  loading.value = true
  errorMessage.value = ''
  try {
    if (force) {
      invalidateAdminDirectory()
      invalidateSeatDirectory()
    }
    const [roomList, dir] = await Promise.all([
      listRooms(),
      loadAdminDirectory(force).catch(() => null),
    ])
  rooms.value = roomList
  directory.value = dir
  directoryFailed.value = dir === null
  void scope.ensureLoaded(force)
  const maxPage = Math.max(1, Math.ceil(roomList.length / pageSize.value))
  if (page.value > maxPage) page.value = maxPage
} catch (caught) {
  errorMessage.value = toBookingFailure(caught).message
  rooms.value = []
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
}

function onReset(): void {
  keyword.value = ''
  enabledFilter.value = '全部'
  page.value = 1
}

function onPageChange(next: number): void {
  page.value = next
}

function onPageSizeChange(next: number): void {
  pageSize.value = next
  page.value = 1
}

function openCreate(): void {
  editing.value = null
  formVisible.value = true
}

function openEdit(room: Room): void {
  if (!scope.guardRoom(room.id)) return
  editing.value = room
  formVisible.value = true
}

function openAreas(room: Room): void {
  if (!scope.guardRoom(room.id)) return
  activeRoom.value = room
  areaVisible.value = true
}

function openClose(room: Room): void {
  if (!scope.guardRoom(room.id)) return
  activeRoom.value = room
  closeVisible.value = true
}

/** 新增 / 修改自习室；成功后刷新列表与目录（座位数、分区数依赖目录）。 */
async function submitForm(payload: RoomFormPayload): Promise<boolean> {
  const isCreate = editing.value === null
  const enableChanged =
    !isCreate && editing.value !== null && editing.value.enabled !== payload.enabled
  try {
    await ElMessageBox.confirm(
      isCreate
        ? `将新增自习室「${payload.name}」（${payload.location}），开放时间 ${payload.open_time}–${payload.close_time}，容量 ${payload.capacity}。新增不会自动生成座位，需再维护分区与座位。本次操作将记入审计日志，确认提交？`
        : `将修改自习室「${payload.name}」的基本信息${enableChanged ? `，并把启用状态改为「${payload.enabled ? '启用' : '停用'}」` : ''}。注意：「停用」只改自习室自身标记，不会让其座位变为不可预约（该标记不影响座位是否可预约）；如需立即阻止预约请用「临时关闭」。本次操作将记入审计日志，确认提交？`,
      isCreate ? '确认：新增自习室' : '确认：修改自习室',
      { type: 'warning', confirmButtonText: '确认提交', cancelButtonText: '返回修改' },
    )
  } catch {
    return false
  }
  submitting.value = true
  try {
    if (isCreate) {
      // 原因随请求提交，后端需写入 audit_logs（RoomCreate 目前没有 reason 字段，见问题清单）
      await createRoom({
        name: payload.name,
        location: payload.location,
        open_time: payload.open_time,
        close_time: payload.close_time,
        capacity: payload.capacity,
        reason: payload.reason,
      })
    ElMessage.success(`已新增自习室「${payload.name}」：请继续维护其分区与座位`)
  } else {
    await updateRoom(editing.value!.id, {
      name: payload.name,
      location: payload.location,
      open_time: payload.open_time,
      close_time: payload.close_time,
      capacity: payload.capacity,
      enabled: payload.enabled,
      reason: payload.reason,
    })
  ElMessage.success(`已保存自习室「${payload.name}」的修改`)
}
formVisible.value = false
await refresh()
return true
} catch (caught) {
  // 失败只弹提示，不把列表整体切成失败态（列表本身仍然可用）
  ElMessage.error(toBookingFailure(caught).message)
  return false
} finally {
  submitting.value = false
}
}

function seatCount(roomId: number): number {
  return seatCountOfRoom(directory.value, roomId)
}

function areaCount(roomId: number): number {
  return areaCountOfRoom(directory.value, roomId)
}

return {
  scope,
  /** 直接暴露范围文案（模板里无需再取 .value） */
  scopeLabel: scope.scopeLabel,
  rooms,
  directory,
  loading,
  refreshing,
  errorMessage,
  directoryFailed,
  keyword,
  enabledFilter,
  page,
  pageSize,
  filtered,
  total,
  paged,
  formVisible,
  editing,
  submitting,
  areaVisible,
  closeVisible,
  activeRoom,
  load,
  refresh,
  onSearch,
  onReset,
  onPageChange,
  onPageSizeChange,
  openCreate,
  openEdit,
  openAreas,
  openClose,
  submitForm,
  seatCount,
  areaCount,
}
}
