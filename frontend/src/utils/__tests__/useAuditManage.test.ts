import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { AuditLog } from '@/types'
import type { AdminDirectory } from '@/utils/adminData'
import { useAuditManage } from '@/utils/useAuditManage'

const mocks = vi.hoisted(() => ({
  listAuditLogs: vi.fn(),
  loadAdminDirectory: vi.fn(),
}))

vi.mock('@/api/audit', () => ({ listAuditLogs: mocks.listAuditLogs }))
vi.mock('@/utils/adminData', () => ({
  loadAdminDirectory: mocks.loadAdminDirectory,
}))
vi.mock('@/utils/bookingData', () => ({
  toBookingFailure: () => ({ message: '加载失败' }),
}))

function auditLog(overrides: Partial<AuditLog> = {}): AuditLog {
  return {
    id: 1,
    operator_id: 7,
    action_type: 'LOGIN_FAILED',
    target_type: 'USER',
    target_id: 7,
    reason: '学号「S0001」凭证错误',
    before_value: null,
    after_value: null,
    created_at: '2026-11-26 10:00:00',
    ...overrides,
  }
}

function page(items: AuditLog[], total = items.length) {
  return { items, total, page: 1, page_size: 20 }
}

describe('useAuditManage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.listAuditLogs.mockResolvedValue(page([]))
    mocks.loadAdminDirectory.mockResolvedValue(null)
  })

  it('空筛选只传分页参数，不伪造空字符串条件', async () => {
    const vm = useAuditManage()

    await vm.load()

    expect(mocks.listAuditLogs).toHaveBeenCalledWith({
      action_type: undefined,
      operator_id: undefined,
      target_type: undefined,
      created_from: undefined,
      created_to: undefined,
      page: 1,
      page_size: 20,
    })
  })

  it('筛选条件与日期区间原样透传', async () => {
    const vm = useAuditManage()
    vm.actionType.value = 'LOGIN_FAILED'
    vm.operatorId.value = 7
    vm.targetType.value = 'USER'
    vm.dateRange.value = ['2026-11-01', '2026-11-26']
    vm.page.value = 2

    await vm.load()

    expect(mocks.listAuditLogs).toHaveBeenCalledWith({
      action_type: 'LOGIN_FAILED',
      operator_id: 7,
      target_type: 'USER',
      created_from: '2026-11-01',
      created_to: '2026-11-26',
      page: 2,
      page_size: 20,
    })
  })

  it('当前页为空时自动退回上一页再查一次', async () => {
    const vm = useAuditManage()
    vm.page.value = 2

    await vm.load()

    expect(vm.page.value).toBe(1)
    expect(mocks.listAuditLogs).toHaveBeenCalledTimes(2)
    expect(mocks.listAuditLogs).toHaveBeenLastCalledWith(expect.objectContaining({ page: 1 }))
  })

  it('加载失败时清空列表并给出可读错误', async () => {
    mocks.listAuditLogs.mockRejectedValue(new Error('boom'))
    const vm = useAuditManage()

    await vm.load()

    expect(vm.items.value).toEqual([])
    expect(vm.total.value).toBe(0)
    expect(vm.errorMessage.value).toBe('加载失败')
    expect(vm.loading.value).toBe(false)
  })

  it('重置筛选会清空条件并回到第一页', async () => {
    const vm = useAuditManage()
    vm.actionType.value = 'LOGOUT'
    vm.operatorId.value = 7
    vm.targetType.value = 'USER'
    vm.dateRange.value = ['2026-11-01', '2026-11-26']
    vm.page.value = 3

    vm.onReset()

    expect(vm.actionType.value).toBe('')
    expect(vm.operatorId.value).toBe('')
    expect(vm.targetType.value).toBe('')
    expect(vm.dateRange.value).toEqual([])
    expect(vm.page.value).toBe(1)
    await vi.waitFor(() => expect(mocks.listAuditLogs).toHaveBeenCalled())
  })

  it('修改每页条数时回到第一页', async () => {
    const vm = useAuditManage()
    vm.page.value = 4

    vm.onPageSizeChange(50)

    expect(vm.pageSize.value).toBe(50)
    expect(vm.page.value).toBe(1)
    await vi.waitFor(() =>
      expect(mocks.listAuditLogs).toHaveBeenLastCalledWith(
        expect.objectContaining({ page: 1, page_size: 50 }),
      ),
    )
  })

  it('操作人下拉来自管理端用户目录', async () => {
    mocks.loadAdminDirectory.mockResolvedValue({
      users: [{ id: 7, name: '管理员', student_no: 'ADM07' }],
    } as unknown as AdminDirectory)
    mocks.listAuditLogs.mockResolvedValue(page([auditLog()]))
    const vm = useAuditManage()

    await vm.load()

    expect(vm.operatorOptions.value).toEqual([{ id: 7, label: '管理员（ADM07）' }])
  })
})
