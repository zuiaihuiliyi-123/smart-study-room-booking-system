/**
 * 站内消息 store（FR-060 / SCOPE-07）。
 *
 * 与旧实现的区别：**列表改为服务端分页 + 服务端类型筛选**，不再一次性拉全量
 * （旧实现最多 500 条，超过即静默截断）。
 *
 * 未读数单独取 `GET /messages/unread-count`：分页后列表不再包含全部消息，
 * 若仍从前端 items 统计未读，角标会随分页变化而不准。
 *
 * 首页未读摘要用 `loadDigest()`：取最近一页并筛出未读前 N 条，与角标共用同一份未读数。
 */
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getUnreadCount, listMyMessages, markMessageRead } from '@/api/message'
import { useAuthStore } from '@/stores/auth'
import type { StationMessage } from '@/types'
import { toBookingFailure } from '@/utils/bookingData'

/** 消息类型（与后端 `MessageType` 枚举保持一致）。 */
export const MESSAGE_TYPES = ['预约通知', '违约通知', '投诉反馈', '系统通知'] as const

/** 「全部标为已读」的扫描上限：后端只有逐条标记接口，避免请求量失控。 */
const MARK_ALL_MAX_PAGES = 5
const MARK_ALL_PAGE_SIZE = 100

export const useMessageStore = defineStore('messages', () => {
  const auth = useAuthStore()

  /** 当前页的消息列表 */
  const items = ref<StationMessage[]>([])
  /** 首页摘要用的未读消息（最多 3 条） */
  const digestItems = ref<StationMessage[]>([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(10)
  /** 类型筛选：'all' 表示全部 */
  const type = ref<string>('all')
  const unreadCount = ref(0)
  const loading = ref(false)
  const errorMessage = ref('')

  /** 上一次加载所属用户；换账号后先清空，避免短暂显示上一个账号的消息。 */
  let ownerId: number | null = null

  const hasUnread = computed(() => unreadCount.value > 0)

  function ensureOwner(): void {
    const currentOwner = auth.user?.id ?? null
    if (ownerId !== null && ownerId !== currentOwner) {
      items.value = []
      digestItems.value = []
      total.value = 0
      unreadCount.value = 0
    }
    ownerId = currentOwner
  }

  /** 未读数：与分页解耦，任何页面/分页下都以服务端为准。 */
  async function loadUnreadCount(): Promise<void> {
    ensureOwner()
    try {
      unreadCount.value = (await getUnreadCount()).count
    } catch {
      // 角标失败不打断页面；下次加载会重试
    }
  }

  /**
   * 加载消息列表（服务端分页）。
   * @param reset 是否回到第一页（切换类型筛选时传 true）
   */
  async function load(reset = false): Promise<void> {
    ensureOwner()
    if (reset) page.value = 1
    loading.value = true
    errorMessage.value = ''
    try {
      const result = await listMyMessages({
        page: page.value,
        page_size: pageSize.value,
        type: type.value === 'all' ? undefined : type.value,
      })
      items.value = result.items
      total.value = result.total
      await loadUnreadCount()
    } catch (caught) {
      errorMessage.value = toBookingFailure(caught).message
    } finally {
      loading.value = false
    }
  }

  /** 首页未读摘要：取最近一页的未读前 N 条，并同步未读数。 */
  async function loadDigest(limit = 3): Promise<void> {
    ensureOwner()
    try {
      const result = await listMyMessages({ page: 1, page_size: 20 })
      digestItems.value = result.items.filter((item) => !item.is_read).slice(0, limit)
      await loadUnreadCount()
    } catch {
      // 首页摘要失败不阻塞主流程
    }
  }

  /** 标记已读：先改本地让角标即时变化，服务端失败则回滚。 */
  async function markRead(messageId: number): Promise<void> {
    const target =
      items.value.find((item) => item.id === messageId) ??
      digestItems.value.find((item) => item.id === messageId)
    if (!target || target.is_read) return
    target.is_read = true
    digestItems.value = digestItems.value.filter((item) => item.id !== messageId)
    unreadCount.value = Math.max(0, unreadCount.value - 1)
    try {
      await markMessageRead(messageId)
    } catch (caught) {
      target.is_read = false
      unreadCount.value += 1
      throw caught
    }
  }

  /**
   * 全部标为已读（兼容旧的单条接口）。
   *
   * 后端只有逐条 `POST /messages/{id}/read`，因此先扫描最近若干页取出未读，
   * 再按小批并发逐条标记；返回成功标记的条数。
   * 说明：受扫描上限约束，极老的未读消息可能不在本次扫描范围内。
   */
  async function markAllRead(): Promise<number> {
    const collected: StationMessage[] = []
    for (let p = 1; p <= MARK_ALL_MAX_PAGES; p += 1) {
      const result = await listMyMessages({ page: p, page_size: MARK_ALL_PAGE_SIZE })
      collected.push(...result.items)
      if (result.items.length === 0 || collected.length >= result.total) break
    }
    const targets = collected.filter((item) => !item.is_read)
    if (targets.length === 0) return 0

    const BATCH_SIZE = 4
    const failed: StationMessage[] = []
    for (let index = 0; index < targets.length; index += BATCH_SIZE) {
      const slice = targets.slice(index, index + BATCH_SIZE)
      const results = await Promise.allSettled(slice.map((item) => markMessageRead(item.id)))
      results.forEach((result, offset) => {
        const item = slice[offset]
        if (result.status === 'rejected' && item) failed.push(item)
      })
    }

    await load()
    if (failed.length > 0) {
      throw new Error(`还有 ${failed.length} 条没有标记成功，请刷新后重试`)
    }
    return targets.length
  }

  function reset(): void {
    items.value = []
    digestItems.value = []
    total.value = 0
    page.value = 1
    type.value = 'all'
    unreadCount.value = 0
    errorMessage.value = ''
    ownerId = null
  }

  return {
    items,
    digestItems,
    total,
    page,
    pageSize,
    type,
    unreadCount,
    hasUnread,
    loading,
    errorMessage,
    load,
    loadUnreadCount,
    loadDigest,
    markRead,
    markAllRead,
    reset,
  }
})
