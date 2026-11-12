import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as messageApi from '@/api/message'
import { useAuthStore } from '@/stores/auth'
import { useMessageStore } from '@/stores/message'
import type { CurrentUser, PageResult, StationMessage } from '@/types'

vi.mock('@/api/message', () => ({
  listMyMessages: vi.fn(),
  getUnreadCount: vi.fn(),
  markMessageRead: vi.fn(),
}))

const user: CurrentUser = {
  id: 1,
  name: '演示学生',
  student_no: 'student',
  role: '学生用户',
  account_status: '正常',
  violation_count: 0,
  contact: null,
}

const message = (overrides: Partial<StationMessage> = {}): StationMessage => ({
  id: 1,
  type: '预约通知',
  title: '预约成功',
  content: '内容',
  related_type: '预约单',
  related_id: 12,
  is_read: false,
  created_at: '2026-11-12 10:00:00',
  ...overrides,
})

const page = (items: StationMessage[]): PageResult<StationMessage> => ({
  items,
  total: items.length,
  page: 1,
  page_size: 10,
})

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  const auth = useAuthStore()
  auth.user = user
})

describe('message store 列表与未读数', () => {
  it('load 同时刷新列表、总数与未读数', async () => {
    vi.mocked(messageApi.listMyMessages).mockResolvedValue(
      page([message({ id: 1 }), message({ id: 2, is_read: true })]),
    )
    vi.mocked(messageApi.getUnreadCount).mockResolvedValue({ count: 1 })

    const store = useMessageStore()
    await store.load()

    expect(store.items).toHaveLength(2)
    expect(store.total).toBe(2)
    expect(store.unreadCount).toBe(1)
    expect(store.hasUnread).toBe(true)
    expect(store.loading).toBe(false)
    expect(messageApi.listMyMessages).toHaveBeenCalledWith({
      page: 1,
      page_size: 10,
      type: undefined,
    })
  })

  it('loadDigest 只保留最近未读，并同步未读数', async () => {
    vi.mocked(messageApi.listMyMessages).mockResolvedValue(
      page([
        message({ id: 1 }),
        message({ id: 2, is_read: true }),
        message({ id: 3 }),
        message({ id: 4 }),
        message({ id: 5 }),
      ]),
    )
    vi.mocked(messageApi.getUnreadCount).mockResolvedValue({ count: 4 })

    const store = useMessageStore()
    await store.loadDigest()

    expect(store.digestItems.map((item) => item.id)).toEqual([1, 3, 4])
    expect(store.unreadCount).toBe(4)
  })
})

describe('message store 标记已读', () => {
  it('先本地生效，失败时回滚', async () => {
    vi.mocked(messageApi.listMyMessages).mockResolvedValue(page([message({ id: 1 })]))
    vi.mocked(messageApi.getUnreadCount).mockResolvedValue({ count: 1 })
    vi.mocked(messageApi.markMessageRead).mockRejectedValue(new Error('network'))

    const store = useMessageStore()
    await store.load()
    const target = store.items[0]

    await expect(store.markRead(1)).rejects.toThrow('network')
    expect(target.is_read).toBe(false)
    expect(store.unreadCount).toBe(1)

    vi.mocked(messageApi.markMessageRead).mockResolvedValue(message({ id: 1, is_read: true }))
    await store.markRead(1)
    expect(target.is_read).toBe(true)
    expect(store.unreadCount).toBe(0)
  })

  it('已读消息重复标记不会发请求', async () => {
    vi.mocked(messageApi.listMyMessages).mockResolvedValue(
      page([message({ id: 1, is_read: true })]),
    )
    vi.mocked(messageApi.getUnreadCount).mockResolvedValue({ count: 0 })

    const store = useMessageStore()
    await store.load()
    await store.markRead(1)

    expect(messageApi.markMessageRead).not.toHaveBeenCalled()
  })
})

describe('message store 账号切换', () => {
  it('换账号后清空上一个账号的列表与未读数', async () => {
    vi.mocked(messageApi.listMyMessages).mockResolvedValue(page([message({ id: 1 })]))
    vi.mocked(messageApi.getUnreadCount).mockResolvedValue({ count: 1 })

    const store = useMessageStore()
    await store.load()
    expect(store.items).toHaveLength(1)

    const auth = useAuthStore()
    auth.user = { ...user, id: 2 }
    await store.loadUnreadCount()

    expect(store.items).toEqual([])
    expect(store.total).toBe(0)
    expect(store.unreadCount).toBe(1)
  })

  it('reset 清空所有状态', async () => {
    vi.mocked(messageApi.listMyMessages).mockResolvedValue(page([message({ id: 1 })]))
    vi.mocked(messageApi.getUnreadCount).mockResolvedValue({ count: 1 })

    const store = useMessageStore()
    await store.load()
    store.reset()

    expect(store.items).toEqual([])
    expect(store.digestItems).toEqual([])
    expect(store.total).toBe(0)
    expect(store.unreadCount).toBe(0)
    expect(store.page).toBe(1)
    expect(store.type).toBe('all')
  })
})
