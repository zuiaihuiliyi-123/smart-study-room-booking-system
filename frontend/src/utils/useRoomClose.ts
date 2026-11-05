/**
 * 「场地临时关闭」的状态机（FR-016 + BR-019 + BR-022）。
 *
 * 交互刻意分成两步，与需求条文一一对应：
 * 1. 填关闭范围与窗口 → `preview()`（只读，不产生任何变化）；
 * 2. `execute()` 前必须已有清单 → 二次确认（含审计提示）→ 才真正执行。
 *
 * 执行语义：
 * - 后端写入一条**带时间窗的关闭记录**，只在 [start_at, end_at) 内生效，窗口结束自动失效；
 * - 座位资源状态（可用 / 维修中 / 停用）**不被改写**，关闭期间只影响该时段的预约；
 * - 受影响预约默认保持原状态（BR-019），仅当明确勾选时按 BR-022 批量取消，不计违约。
 *
 * 管理员可在抽屉里看到「进行中」的关闭记录，并随时提前解除。
 */
import { computed, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

import { closeRoom, listRoomClosures, previewRoomClose, releaseRoomClosure } from '@/api/room'
import type { ConflictPreview, Reservation, Room, RoomClosure } from '@/types'
import { areaLabelOf, invalidateAdminDirectory, type AdminDirectory } from '@/utils/adminData'
import { toBookingFailure } from '@/utils/bookingData'

export function useRoomClose() {
  const room = ref<Room | null>(null)
  const directory = ref<AdminDirectory | null>(null)

  const areaId = ref(0)
  const dateRange = ref<string[]>([])
  const startTime = ref('08:00')
  const endTime = ref('22:00')
  const reason = ref('')

  const queried = ref(false)
  const previewLoading = ref(false)
  const previewError = ref('')
  const previewResult = ref<ConflictPreview | null>(null)
  const cancelAffected = ref(false)
  const executing = ref(false)

  const closures = ref<RoomClosure[]>([])
  const closuresLoading = ref(false)
  const releasingId = ref<number | null>(null)

  const areaOptions = computed(() => directory.value?.areasByRoom.get(room.value?.id ?? 0) ?? [])
  const startAt = computed(() =>
      dateRange.value.length === 2 ? `${dateRange.value[0]}T${startTime.value}` : '',
  )
  const endAt = computed(() =>
      dateRange.value.length === 2 ? `${dateRange.value[1]}T${endTime.value}` : '',
  )
  const windowError = computed(() => {
    if (startAt.value === '' || endAt.value === '') return '请选择关闭日期区间'
    return dayjs(endAt.value).isAfter(dayjs(startAt.value))
      ? ''
      : '关闭窗口不合法：结束时刻必须晚于开始时刻'
  })
const reservations = computed<Reservation[]>(() => previewResult.value?.reservations ?? [])

async function loadClosures(): Promise<void> {
  if (room.value === null) return
  closuresLoading.value = true
  try {
    closures.value = await listRoomClosures(room.value.id)
  } catch {
    closures.value = []
  } finally {
    closuresLoading.value = false
  }
}

function open(target: Room, dir: AdminDirectory | null): void {
  room.value = target
  directory.value = dir
  const today = dayjs()
  dateRange.value = [today.format('YYYY-MM-DD'), today.add(6, 'day').format('YYYY-MM-DD')]
  startTime.value = '08:00'
  endTime.value = '22:00'
  areaId.value = 0
  reason.value = ''
  queried.value = false
  previewError.value = ''
  previewResult.value = null
  cancelAffected.value = false
  closures.value = []
  void loadClosures()
}

/** 提前解除一条关闭记录（原因必填）。 */
async function releaseClosure(closure: RoomClosure): Promise<void> {
  if (room.value === null) return
  let input = ''
  try {
    const result = await ElMessageBox.prompt(
      `确认解除 ${dayjs(closure.start_at).format('MM-DD HH:mm')}–${dayjs(closure.end_at).format('HH:mm')} 的临时关闭？解除后该时段立即恢复可约。`,
      '解除临时关闭',
      {
        confirmButtonText: '确认解除',
        cancelButtonText: '返回',
        inputPlaceholder: '请填写解除原因（记入审计日志）',
        inputValidator: (value: string) => (value.trim() === '' ? '解除原因不能为空' : true),
      },
    )
    input = result.value.trim()
  } catch {
    return
  }
  releasingId.value = closure.id
  try {
    await releaseRoomClosure(room.value.id, closure.id, input)
    ElMessage.success('已解除该临时关闭，该时段恢复可约')
    await loadClosures()
  } catch (caught) {
    ElMessage.error(toBookingFailure(caught).message)
  } finally {
    releasingId.value = null
  }
}

/** 影响窗口一旦变化，之前查询的清单即失效，必须重新查询（避免拿旧清单确认新窗口） */
function invalidatePreview(): void {
  if (!queried.value) return
  queried.value = false
  previewResult.value = null
  cancelAffected.value = false
}

async function loadPreview(): Promise<void> {
  if (room.value === null) return
  if (windowError.value !== '') {
    ElMessage.warning(windowError.value)
    return
  }
  previewLoading.value = true
  previewError.value = ''
  try {
    previewResult.value = await previewRoomClose(room.value.id, {
      start_at: startAt.value,
      end_at: endAt.value,
      area_id: areaId.value === 0 ? undefined : areaId.value,
    })
  queried.value = true
  cancelAffected.value = false
} catch (caught) {
  previewError.value = toBookingFailure(caught).message
  previewResult.value = null
} finally {
  previewLoading.value = false
}
}

/** BR-022：二次确认后执行；`expected_reservation_ids` 用于防止清单在确认期间发生变化 */
async function execute(): Promise<boolean> {
  if (room.value === null || previewResult.value === null) return false
  if (windowError.value !== '') {
    ElMessage.warning(windowError.value)
    return false
  }
  if (reason.value.trim() === '') {
    ElMessage.warning('请填写关闭原因：原因会写入审计日志')
    return false
  }

  const count = reservations.value.length
  const cancelLine =
    cancelAffected.value && count > 0
    ? `同时批量取消 ${count} 条受影响预约（不计违约、无补偿、不支持改约）`
    : `保留 ${count} 条受影响预约的原状态（默认保留并持续提示）`
  const scopeLine =
    areaId.value === 0 ? '整个自习室' : `分区 ${areaLabelOf(directory.value, areaId.value)}`

  try {
    await ElMessageBox.confirm(
      `关闭范围：${room.value.name}（${scopeLine}）；关闭时段：${startAt.value.replace('T', ' ')} ~ ${endAt.value.replace('T', ' ')}。处理方式：${cancelLine}。本次操作将记入审计日志。确认执行？`,
      '确认操作：场地临时关闭',
      { type: 'warning', confirmButtonText: '确认执行', cancelButtonText: '返回检查' },
    )
  } catch {
    return false
  }

  executing.value = true
  try {
    const result = await closeRoom(room.value.id, {
      start_at: startAt.value,
      end_at: endAt.value,
      area_id: areaId.value === 0 ? undefined : areaId.value,
      reason: reason.value.trim(),
      cancel_affected: cancelAffected.value,
      expected_reservation_ids: reservations.value.map((item) => item.id),
    })
  ElMessage.success(
    `已临时关闭 ${result.closed_seats} 个座位所在的时段：取消预约 ${result.cancelled} 条，保留 ${result.kept} 条；窗口结束后自动恢复。`,
  )
  invalidateAdminDirectory()
  await loadClosures()
  return true
} catch (caught) {
  ElMessage.error(toBookingFailure(caught).message)
  return false
} finally {
  executing.value = false
}
}

return {
  room,
  directory,
  areaId,
  dateRange,
  startTime,
  endTime,
  reason,
  queried,
  previewLoading,
  previewError,
  cancelAffected,
  executing,
  closures,
  closuresLoading,
  releasingId,
  areaOptions,
  startAt,
  endAt,
  windowError,
  reservations,
  open,
  invalidatePreview,
  preview: loadPreview,
  execute,
  releaseClosure,
}
}

