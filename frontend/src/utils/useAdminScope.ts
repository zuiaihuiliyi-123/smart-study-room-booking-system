/**
 * 管理端「操作范围」的唯一判定点。
 *
 * CF-02（管理员分级）在需求侧**尚未确认**：需求规格说明书第 4.1.2 节与 BR-018 的本版口径为
 * 「本版按管理员不分级定稿，任一管理员可操作全部座位资源」。为避免把这一临时口径散落到
 * 每个页面，本文件把它收敛成唯一判定点：**将来引入分级（按自习室授权）时只改这里**，
 * 各页面继续调用 `canOperateRoom / canOperateSeat / guard*`，不需要改动。
 *
 * 对应的需求依据：
 * - FR-004 前置条件：操作者在其被授权的自习室范围内
 * - ST-007 / ST-048：越权操作被拒绝并写越权审计日志
 * - 第 4.1.2 节：本版按「管理员不分级」建模，单自习室部署下 E2 分支不产生差异
 */
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'

import { listRooms } from '@/api/room'
import { useAuthStore } from '@/stores/auth'
import type { Room, Seat } from '@/types'
import { toBookingFailure } from '@/utils/bookingData'

const rooms = ref<Room[]>([])
const loading = ref(false)
const loaded = ref(false)
const errorMessage = ref('')

let pending: Promise<void> | null = null

async function fetchRooms(force = false): Promise<void> {
  if (pending !== null) return pending
  if (loaded.value && !force) return
  loading.value = true
  errorMessage.value = ''
  pending = listRooms()
    .then((list) => {
    rooms.value = list
    loaded.value = true
  })
  .catch((caught: unknown) => {
  errorMessage.value = toBookingFailure(caught).message
  rooms.value = []
})
  .finally(() => {
  loading.value = false
  pending = null
})
return pending
}

export function useAdminScope() {
  const auth = useAuthStore()

  /**
   * 分级开关：本版恒为 true（不分级）。引入分级后改为按 `auth.user` 的授权自习室集合计算。
   * 页面不要直接读它做业务判断，只用于展示口径说明。
   */
  const unleveled = computed(() => true)

  /** 当前管理员可操作的自习室；不分级时即全部启用与非启用的自习室 */
  const scopedRooms = computed<Room[]>(() => (unleveled.value ? rooms.value : []))

  const scopeRoomIds = computed<number[]>(() => scopedRooms.value.map((item) => item.id))

  /** 界面与审计提示里统一使用的范围说明 */
  const scopeLabel = computed(() =>
      unleveled.value
      ? `全部自习室（本版按管理员不分级建模；当前共 ${rooms.value.length} 间）`
      : `授权范围内自习室（${rooms.value.length} 间）`,
  )

  function canOperateRoom(roomId: number): boolean {
    if (!auth.isAdmin) return false
    if (unleveled.value) return true
    return scopeRoomIds.value.includes(roomId)
  }

  function canOperateSeat(seat: Pick<Seat, 'room_id'> | null | undefined): boolean {
    if (!seat) return false
    return canOperateRoom(seat.room_id)
  }

  /** 动作前的范围校验：越权时按 ST-007 提示并返回 false，调用方直接 return */
  function guardRoom(roomId: number): boolean {
    if (canOperateRoom(roomId)) return true
    ElMessage.warning('无权限操作该资源：目标不在你的授权自习室范围内')
    return false
  }

  function guardSeat(seat: Pick<Seat, 'room_id'> | null | undefined): boolean {
    if (seat && canOperateSeat(seat)) return true
    ElMessage.warning('无权限操作该资源：目标不在你的授权自习室范围内')
    return false
  }

  return {
    rooms,
    loading,
    loaded,
    errorMessage,
    unleveled,
    scopedRooms,
    scopeRoomIds,
    scopeLabel,
    canOperateRoom,
    canOperateSeat,
    guardRoom,
    guardSeat,
    ensureLoaded: fetchRooms,
  }
}
