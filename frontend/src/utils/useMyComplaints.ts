/**
 * 「我的投诉」页状态机（FR-042 提交 + FR-043 查看处理进度）。
 *
 * 口径来源：
 * - BR-014：投诉自提交起 **3 个工作日**内应给出处理结果；初始状态「待处理」（ST-060）。
 * - 投诉对象为 4 类（座位 / 自习室 / 预约单 / 用户），提交时必须给出对象标识。
 * - 内容长度：任务书要求 ≤500 字（界面限制）。服务端目前允许到 1000 字，
 *   界面更严格不会导致服务端拒绝；差异已登记在本轮问题清单。
 */
import { nextTick, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'

import { createComplaint, listMyComplaints } from '@/api/complaint'
import { listRooms } from '@/api/room'
import type { TargetType } from '@/components/complaints/complaintMeta'
import type { Complaint, Reservation, Room } from '@/types'
import {
  fetchAllMyReservations,
  loadSeatDirectory,
  toBookingFailure,
  type SeatRef,
} from '@/utils/bookingData'
import { parseFocusId } from '@/utils/messageLinks'

export interface ComplaintFormPayload {
  target_type: TargetType
  target_id: number
  content: string
}

export function useMyComplaints() {
  const route = useRoute()

  const items = ref<Complaint[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(10)
  const loading = ref(true)
  const errorMessage = ref('')
  const submitting = ref(false)
  /** 最近一次提交成功的投诉编号：用于列表高亮并滚动到该条 */
  const newId = ref<number | null>(null)
  const focusId = ref<number | null>(parseFocusId(route.query.focus))

  const rooms = ref<Room[]>([])
  const seats = ref<SeatRef[]>([])
  const reservations = ref<Reservation[]>([])

  async function load(): Promise<void> {
    loading.value = true
    errorMessage.value = ''
    try {
      const result = await listMyComplaints({ page: page.value, page_size: pageSize.value })
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

  /** 表单候选项：自习室、座位、本人预约单。失败时降级为空候选项，不阻塞提交表单。 */
  async function loadOptions(): Promise<void> {
    const [roomList, directory, myReservations] = await Promise.all([
      listRooms().catch(() => [] as Room[]),
      loadSeatDirectory().catch(() => null),
      fetchAllMyReservations().catch(() => [] as Reservation[]),
    ])
  rooms.value = roomList
  seats.value = directory === null ? [] : [...directory.values()]
  reservations.value = myReservations
}

async function submit(payload: ComplaintFormPayload): Promise<void> {
  submitting.value = true
  try {
    const created = await createComplaint({
      target_type: payload.target_type,
      target_id: payload.target_id,
      content: payload.content.trim(),
    })
  ElMessage.success(
    `投诉已提交（#${created.id}），当前状态「${created.status}」；处理时限为 3 个工作日`,
  )
  newId.value = created.id
  page.value = 1
  await load()
  await nextTick()
  document
    .querySelector('.complaint--new')
    ?.scrollIntoView({ block: 'center', behavior: 'smooth' })
} catch {
  // 失败提示由 request.ts 拦截器统一给出；表单内容保留，便于修正后重提
} finally {
  submitting.value = false
}
}

function onPageChange(next: number): void {
  page.value = next
  newId.value = null
  focusId.value = null
  void load()
}

async function bootstrap(): Promise<void> {
  await Promise.all([load(), loadOptions()])
}

return {
  items,
  total,
  page,
  pageSize,
  loading,
  errorMessage,
  submitting,
  newId,
  focusId,
  rooms,
  seats,
  reservations,
  load,
  submit,
  bootstrap,
  onPageChange,
}
}
