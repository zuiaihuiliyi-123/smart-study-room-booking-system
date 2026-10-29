/**
 * 「用户管理」页状态机（FR-040）。
 *
 * **只读**页面：管理员可查询用户基本信息与账户状态，但按 BR-018 / Q-030 的本版裁定，
 * **不得编辑姓名、学号等身份信息与口令**，也不得代改联系方式（联系方式是用户唯一可自行修改的字段）。
 * 因此本页不提供任何编辑入口；账户状态的变更一律走 FR-044 的黑名单流程（另一页）。
 *
 * 脱敏（NFR-006）：手机号与邮箱在界面上必须掩码，掩码逻辑集中在 `utils/mask.ts`。
 */
import { ref } from 'vue'

import { listUsers } from '@/api/user'
import type { CurrentUser } from '@/types'
import { toBookingFailure } from '@/utils/bookingData'
import { useAdminScope } from '@/utils/useAdminScope'

export type UserRoleFilter = '全部' | '学生用户' | '教师用户' | '自习室管理员' | '系统管理员'
export type UserStatusFilter = '全部' | '正常' | '受限' | '停用'

export function useUserManage() {
  const scope = useAdminScope()

  const items = ref<CurrentUser[]>([])
  const total = ref(0)
  const loading = ref(true)
  const refreshing = ref(false)
  const errorMessage = ref('')

  const keyword = ref('')
  const roleFilter = ref<UserRoleFilter>('全部')
  const statusFilter = ref<UserStatusFilter>('全部')
  const violationMin = ref<number | null>(null)
  const page = ref(1)
  const pageSize = ref(20)

  const detailVisible = ref(false)
  const detail = ref<CurrentUser | null>(null)

  async function load(): Promise<void> {
    loading.value = true
    errorMessage.value = ''
    try {
      const result = await listUsers({
        page: page.value,
        page_size: pageSize.value,
        keyword: keyword.value.trim() === '' ? undefined : keyword.value.trim(),
        role: roleFilter.value === '全部' ? undefined : roleFilter.value,
        account_status: statusFilter.value === '全部' ? undefined : statusFilter.value,
        violation_min: violationMin.value ?? undefined,
      })
    items.value = result.items
    total.value = result.total
    if (items.value.length === 0 && page.value > 1) {
      page.value -= 1
      await load()
    }
    void scope.ensureLoaded()
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
    await load()
  } finally {
    refreshing.value = false
  }
}

function onSearch(): void {
  page.value = 1
  void load()
}

function onReset(): void {
  keyword.value = ''
  roleFilter.value = '全部'
  statusFilter.value = '全部'
  violationMin.value = null
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

function openDetail(item: CurrentUser): void {
  detail.value = item
  detailVisible.value = true
}

return {
  scopeLabel: scope.scopeLabel,
  items,
  total,
  loading,
  refreshing,
  errorMessage,
  keyword,
  roleFilter,
  statusFilter,
  violationMin,
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
