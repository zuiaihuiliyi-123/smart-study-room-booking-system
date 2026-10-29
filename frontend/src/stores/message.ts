/**
 * 站内消息 store（FR-060 / SCOPE-07）——全站唯一数据源。
 *
 * 为什么必须只有一个来源：未读数同时出现在三处（顶栏铃铛角标、首页未读摘要、
 * 站内消息列表）。三处各自取数会出现「角标 3 / 列表 2 条未读」这类不一致，
 * 因此铃铛（StudentLayout）、首页摘要（HomeView）与列表页（MessagesView）
 * 统一读写本 store，`load()` 自带去重（已加载则不重复请求）。
 *
 * 已知接口限制：`/messages/me` 没有「未读数」接口，也没有批量已读接口。
 * 因此这里翻页取全量、由前端统计未读数；标记已读只能逐条调用
 * `POST /messages/{id}/read`（登记在本轮问题清单）。
 */
import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { listMyMessages, markMessageRead } from '@/api/message'
import { useAuthStore } from '@/stores/auth'
import type { StationMessage } from '@/types'
import { toBookingFailure } from '@/utils/bookingData'

/** 翻页取全量：page_size 上限 100（与后端 `le=100` 一致）。 */
async function fetchAllMessages(pageSize = 100, maxPages = 5): Promise<StationMessage[]> {
  const collected: StationMessage[] = []
  for (let page = 1; page <= maxPages; page += 1) {
    const result = await listMyMessages({ page, page_size: pageSize })
    collected.push(...result.items)
    if (result.items.length === 0 || collected.length >= result.total) break
  }
  return collected
}

export const useMessageStore = defineStore('messages', () => {
  const auth = useAuthStore()

  const items = ref<StationMessage[]>([])
  const loading = ref(false)
  const loaded = ref(false)
  const errorMessage = ref('')

  /** 上一次加载所属用户；换账号后先清空，避免短暂显示上一个账号的消息。 */
  let ownerId: number | null = null

  const unreadItems = computed(() => items.value.filter((item) => !item.is_read))
  const unreadCount = computed(() => unreadItems.value.length)

  /** 类型筛选项：按消息里实际出现的类型，不写死枚举。 */
  const types = computed(() => {
    const seen: string[] = []
    for (const item of items.value) {
      if (!seen.includes(item.type)) seen.push(item.type)
    }
    return seen
  })

function reset(): void {
  items.value = []
  loaded.value = false
  errorMessage.value = ''
  ownerId = null
}

/** `force = false` 时只保证「加载过」，供多页共享；显式刷新/重试传 true。 */
async function load(force = false): Promise<void> {
  if (loading.value) return
  if (loaded.value && !force) return

  const currentOwner = auth.user?.id ?? null
  if (ownerId !== null && ownerId !== currentOwner) items.value = []

  loading.value = true
  errorMessage.value = ''
  try {
    items.value = await fetchAllMessages()
    ownerId = currentOwner
    loaded.value = true
  } catch (caught) {
    // 失败提示由 request.ts 拦截器统一给出；此处只保留内联错误态
    errorMessage.value = toBookingFailure(caught).message
  } finally {
    loading.value = false
  }
}

/** 标记已读：先改本地让角标即时变化，服务端失败则回滚。 */
async function markRead(messageId: number): Promise<void> {
  const target = items.value.find((item) => item.id === messageId)
  if (!target || target.is_read) return
  target.is_read = true
  try {
    await markMessageRead(messageId)
  } catch (caught) {
    target.is_read = false
    throw caught
  }
}

return {
  items,
  loading,
  loaded,
  errorMessage,
  unreadItems,
  unreadCount,
  types,
  load,
  markRead,
  reset,
}
})
