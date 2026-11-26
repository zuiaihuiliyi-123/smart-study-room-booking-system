import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Complaint } from '@/types'
import { useMyComplaints } from '@/utils/useMyComplaints'

const mocks = vi.hoisted(() => ({
  listMyComplaints: vi.fn(),
  createComplaint: vi.fn(),
  confirmComplaint: vi.fn(),
  listRooms: vi.fn(),
  fetchAllMyReservations: vi.fn(),
  loadSeatDirectory: vi.fn(),
  success: vi.fn(),
  confirm: vi.fn(),
}))

vi.mock('vue-router', () => ({ useRoute: () => ({ query: {} }) }))
vi.mock('element-plus', () => ({
  ElMessage: { success: mocks.success },
  ElMessageBox: { confirm: mocks.confirm },
}))
vi.mock('@/api/complaint', () => ({
  listMyComplaints: mocks.listMyComplaints,
  createComplaint: mocks.createComplaint,
  confirmComplaint: mocks.confirmComplaint,
}))
vi.mock('@/api/room', () => ({ listRooms: mocks.listRooms }))
vi.mock('@/utils/bookingData', () => ({
  fetchAllMyReservations: mocks.fetchAllMyReservations,
  loadSeatDirectory: mocks.loadSeatDirectory,
  toBookingFailure: () => ({ message: '加载失败' }),
}))
vi.mock('@/utils/messageLinks', () => ({ parseFocusId: () => null }))

function complaint(overrides: Partial<Complaint> = {}): Complaint {
  return {
    id: 1,
    user_id: 1,
    target_type: '自习室',
    target_id: 1,
    content: '空调太冷',
    status: '待处理',
    handler_id: null,
    handle_note: null,
    handled_at: null,
    created_at: '2026-11-26 10:00:00',
    ...overrides,
  }
}

function page(items: Complaint[], total = items.length) {
  return { items, total, page: 1, page_size: 10 }
}

describe('useMyComplaints', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.listRooms.mockResolvedValue([])
    mocks.fetchAllMyReservations.mockResolvedValue([])
    mocks.loadSeatDirectory.mockResolvedValue(new Map())
  })

  it('load 成功时写入列表、总数并结束 loading', async () => {
    mocks.listMyComplaints.mockResolvedValue(page([complaint()], 1))
    const vm = useMyComplaints()

    await vm.load()

    expect(vm.items.value).toHaveLength(1)
    expect(vm.total.value).toBe(1)
    expect(vm.loading.value).toBe(false)
    expect(vm.errorMessage.value).toBe('')
  })

  it('load 失败时清空列表并给出可读错误', async () => {
    mocks.listMyComplaints.mockRejectedValue(new Error('boom'))
    const vm = useMyComplaints()

    await vm.load()

    expect(vm.items.value).toEqual([])
    expect(vm.total.value).toBe(0)
    expect(vm.errorMessage.value).toBe('加载失败')
    expect(vm.loading.value).toBe(false)
  })

  it('submit 去掉内容首尾空格，回到第一页并刷新列表', async () => {
    mocks.createComplaint.mockResolvedValue(complaint({ id: 9, content: '灯光太暗' }))
    mocks.listMyComplaints.mockResolvedValue(page([complaint({ id: 9 })]))
    const vm = useMyComplaints()
    vm.page.value = 3

    await vm.submit({ target_type: '自习室', target_id: 1, content: '  灯光太暗  ' })

    expect(mocks.createComplaint).toHaveBeenCalledWith({
      target_type: '自习室',
      target_id: 1,
      content: '灯光太暗',
    })
    expect(vm.page.value).toBe(1)
    expect(vm.newId.value).toBe(9)
    expect(mocks.success).toHaveBeenCalled()
    expect(mocks.listMyComplaints).toHaveBeenCalled()
  })

  it('confirmClose 对非「已处理」投诉不弹确认框', async () => {
    const vm = useMyComplaints()

    await vm.confirmClose(complaint({ status: '待处理' }))

    expect(mocks.confirm).not.toHaveBeenCalled()
    expect(mocks.confirmComplaint).not.toHaveBeenCalled()
  })

  it('confirmClose 确认后原地替换为「已关闭」', async () => {
    mocks.listMyComplaints.mockResolvedValue(page([complaint({ id: 5, status: '已处理' })]))
    mocks.confirm.mockResolvedValue('confirm')
    mocks.confirmComplaint.mockResolvedValue(complaint({ id: 5, status: '已关闭' }))
    const vm = useMyComplaints()
    await vm.load()

    await vm.confirmClose(vm.items.value[0])

    expect(mocks.confirmComplaint).toHaveBeenCalledWith(5)
    expect(vm.items.value[0].status).toBe('已关闭')
    expect(vm.confirmingId.value).toBeNull()
  })

  it('onPageChange 翻页时清空高亮与聚焦并重新加载', async () => {
    mocks.listMyComplaints.mockResolvedValue(page([]))
    const vm = useMyComplaints()
    vm.newId.value = 1

    vm.onPageChange(2)

    expect(vm.page.value).toBe(2)
    expect(vm.newId.value).toBeNull()
    expect(vm.focusId.value).toBeNull()
    await vi.waitFor(() => expect(mocks.listMyComplaints).toHaveBeenCalled())
  })
})
