/**
 * 「场地临时关闭」的状态机（FR-016 + BR-019 + BR-022）。
 *
 * 交互刻意分成两步，与需求条文一一对应：
 * 1. 填关闭范围与窗口 → `preview()`（只读，不产生任何变化）；
 * 2. `execute()` 前必须已有清单 → 二次确认（含审计提示）→ 才真正执行。
 *
 * 执行语义（取自 FR-016 的状态与数据影响，不自行发挥）：
 * - 座位资源状态 →「停用」；
 * - 受影响预约**默认保持原状态**（BR-019：保留并持续提示）；
 * - 仅当明确勾选时按 BR-022 批量取消，且不计违约、无补偿、不支持改约。
 *
 * 口径提醒：「关闭窗口」只用于圈定受影响预约。座位资源状态是不带时间窗的标记，本版没有
 * 「场地关闭记录」实体，因此关闭后不会自动恢复，需管理员之后手动改回「可用」。
 */
import { computed, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'

import { closeRoom, previewRoomClose } from '@/api/room'
import type { ConflictPreview, Reservation, Room } from '@/types'
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
      `关闭范围：${room.value.name}（${scopeLine}）；关闭窗口：${startAt.value.replace('T', ' ')} ~ ${endAt.value.replace('T', ' ')}（左闭右开）。处理方式：${cancelLine}。本次操作将记入审计日志。确认执行？`,
      '二次确认：场地临时关闭',
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
    `临时关闭已执行：${result.closed_seats} 个座位置为「停用」，取消预约 ${result.cancelled} 条，保留 ${result.kept} 条`,
  )
  invalidateAdminDirectory()
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
  areaOptions,
  startAt,
  endAt,
  windowError,
  reservations,
  open,
  invalidatePreview,
  preview: loadPreview,
  execute,
}
}

