/**
 * 「违约记录管理」页状态机（FR-032）。
 *
 * 只读页面：按「违约类型 / 产生时间区间 / 学号」查询全部违约记录并查看明细。
 * 明确不含导出（FR-033 已裁定排除，AGENTS.md §4），也不提供"撤销违约 / 申诉"入口
 * （FR-024 违约申诉同样已排除）。
 */
import { ref } from 'vue'

import { listAllViolations } from '@/api/violation'
import type { Violation } from '@/types'
import { invalidateAdminDirectory, loadAdminDirectory, type AdminDirectory } from '@/utils/adminData'
import { toBookingFailure } from '@/utils/bookingData'
import { useAdminScope } from '@/utils/useAdminScope'

export type ViolationTypeFilter = '全部' | '自动违约' | '手动违约'

export function useViolationManage() {
  const scope = useAdminScope()

  const directory = ref<AdminDirectory | null>(null)
  const items = ref<Violation[]>([])
  const total = ref(0)
  const loading = ref(true)
  const refreshing = ref(false)
  const errorMessage = ref('')

  const typeFilter = ref<ViolationTypeFilter>('全部')
  const dateRange = ref<string[]>([])
  const studentNo = ref('')
  const page = ref(1)
  const pageSize = ref(20)

  const detailVisible = ref(false)
  const detail = ref<Violation | null>(null)

  async function load(force = false): Promise<void> {
    loading.value = true
    errorMessage.value = ''
    try {
      if (force) invalidateAdminDirectory()
      const [result, dir] = await Promise.all([
        listAllViolations({
          page: page.value,
          page_size: pageSize.value,
          type: typeFilter.value === '全部' ? undefined : typeFilter.value,
          created_from: dateRange.value[0],
          created_to: dateRange.value[1],
          student_no: studentNo.value.trim() === '' ? undefined : studentNo.value.trim(),
        }),
      loadAdminDirectory(force).catch(() => null),
    ])
  items.value = result.items
  total.value = result.total
  directory.value = dir
  if (items.value.length === 0 && page.value > 1) {
    page.value -= 1
    await load()
  }
  void scope.ensureLoaded(force)
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
  typeFilter.value = '全部'
  dateRange.value = []
  studentNo.value = ''
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

function openDetail(item: Violation): void {
  detail.value = item
  detailVisible.value = true
}

return {
  scopeLabel: scope.scopeLabel,
  directory,
  items,
  total,
  loading,
  refreshing,
  errorMessage,
  typeFilter,
  dateRange,
  studentNo,
  page,
  pageSize,
  detailVisible,
  detail,
  load,
  refresh,
  onSearch,
  onReset,
  onPageChange,
  onPageSizeChange,
  openDetail,
}
}
