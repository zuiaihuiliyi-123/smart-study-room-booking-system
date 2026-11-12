/**
 * 「审计日志」页状态机（D2 / NFR-009）。
 *
 * 只读：支持操作类型、操作人、目标类型与操作日期筛选，服务端分页。
 * 不提供修改、删除或导出（FR-033 已排除）。
 */
import { computed, ref } from 'vue'

import { listAuditLogs } from '@/api/audit'
import type { AuditLog } from '@/types'
import { loadAdminDirectory, type AdminDirectory } from '@/utils/adminData'
import { toBookingFailure } from '@/utils/bookingData'

export function useAuditManage() {
  const directory = ref<AdminDirectory | null>(null)
  const items = ref<AuditLog[]>([])
  const total = ref(0)
  const loading = ref(true)
  const refreshing = ref(false)
  const errorMessage = ref('')

  const actionType = ref('')
  const operatorId = ref<number | ''>('')
  const targetType = ref('')
  const dateRange = ref<string[]>([])
  const page = ref(1)
  const pageSize = ref(20)

  const operatorOptions = computed(() =>
    (directory.value?.users ?? []).map((user) => ({
      id: user.id,
      label: `${user.name}（${user.student_no}）`,
    })),
  )

  async function load(force = false): Promise<void> {
    loading.value = true
    errorMessage.value = ''
    try {
      const [result, dir] = await Promise.all([
        listAuditLogs({
          action_type: actionType.value || undefined,
          operator_id: operatorId.value === '' ? undefined : operatorId.value,
          target_type: targetType.value || undefined,
          created_from: dateRange.value[0],
          created_to: dateRange.value[1],
          page: page.value,
          page_size: pageSize.value,
        }),
        loadAdminDirectory(force).catch(() => null),
      ])
      items.value = result.items
      total.value = result.total
      directory.value = dir
      if (items.value.length === 0 && page.value > 1) {
        page.value -= 1
        await load(force)
      }
    } catch (caught) {
      errorMessage.value = toBookingFailure(caught).message
      items.value = []
      total.value = 0
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
    void load()
  }

  function onReset(): void {
    actionType.value = ''
    operatorId.value = ''
    targetType.value = ''
    dateRange.value = []
    page.value = 1
    void load()
  }

  function onPageChange(next: number): void {
    page.value = next
    void load()
  }

  function onPageSizeChange(next: number): void {
    pageSize.value = next
    page.value = 1
    void load()
  }

  return {
    directory,
    items,
    total,
    loading,
    refreshing,
    errorMessage,
    actionType,
    operatorId,
    targetType,
    dateRange,
    page,
    pageSize,
    operatorOptions,
    load,
    refresh,
    onSearch,
    onReset,
    onPageChange,
    onPageSizeChange,
  }
}
