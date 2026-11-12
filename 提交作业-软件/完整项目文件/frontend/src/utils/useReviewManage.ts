/**
 * 「评价管理」页状态机（FR-041 / BR-013）。
 *
 * 管理端只读：评价只能由学生在「已完成」预约上提交，一单一评；
 * 本页提供评分与提交日期筛选，列表与筛选均由服务端分页 / 过滤。
 */
import { ref } from 'vue'

import { listAllReviews } from '@/api/review'
import type { Review } from '@/types'
import { loadAdminDirectory, type AdminDirectory } from '@/utils/adminData'
import { toBookingFailure } from '@/utils/bookingData'

export function useReviewManage() {
  const directory = ref<AdminDirectory | null>(null)
  const items = ref<Review[]>([])
  const total = ref(0)
  const loading = ref(true)
  const refreshing = ref(false)
  const errorMessage = ref('')

  /** 空字符串表示「全部评分」 */
  const scoreFilter = ref<number | ''>('')
  const dateRange = ref<string[]>([])
  const page = ref(1)
  const pageSize = ref(20)

  async function load(force = false): Promise<void> {
    loading.value = true
    errorMessage.value = ''
    try {
      const [result, dir] = await Promise.all([
        listAllReviews({
          score: scoreFilter.value === '' ? undefined : scoreFilter.value,
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
      // 处理完筛选后当前页可能已空（例如从第 2 页切到更窄的条件）
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
    scoreFilter.value = ''
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
    scoreFilter,
    dateRange,
    page,
    pageSize,
    load,
    refresh,
    onSearch,
    onReset,
    onPageChange,
    onPageSizeChange,
  }
}
