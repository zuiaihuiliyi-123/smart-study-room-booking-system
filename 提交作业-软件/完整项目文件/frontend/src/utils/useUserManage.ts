/**
 * 「用户管理」页状态机（FR-040）。
 *
 * 身份信息只读：管理员可查询用户基本信息，但按 BR-018 / Q-030 的本版裁定，
 * **不得编辑姓名、学号等身份信息与口令**，也不得代改联系方式（联系方式是用户唯一可自行修改的字段）。
 *
 * 账户状态：**受限**由黑名单流程产生（FR-044）；**停用 / 恢复**由本页的
 * `PATCH /users/{id}/account-status` 完成（ST-044 / ST-045 / ST-046，须填原因并写审计）。
 * 「受限」账户不能直接停用——须先解除黑名单，避免两类限制互相覆盖。
 *
 * 脱敏（NFR-006）：手机号与邮箱在界面上必须掩码，掩码逻辑集中在 `utils/mask.ts`。
 */
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

import { listUsers, updateUserAccountStatus } from '@/api/user'
import type { CurrentUser } from '@/types'
import { toBookingFailure } from '@/utils/bookingData'
import { useAdminScope } from '@/utils/useAdminScope'

export type UserRoleFilter = '全部' | '学生用户' | '自习室管理员' | '系统管理员'
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

/* ------------------------------ 账户停用 / 恢复（ST-044 / ST-045 / ST-046） */

const statusDialogVisible = ref(false)
const statusTarget = ref<CurrentUser | null>(null)
/** 目标状态：正常账户点「停用」→ 停用；停用账户点「恢复」→ 正常 */
const statusTargetValue = ref<'停用' | '正常'>('停用')
const statusReason = ref('')
const statusSubmitting = ref(false)
const statusError = ref('')

function openStatusDialog(item: CurrentUser): void {
  if (item.account_status === '受限') {
    ElMessage.warning('该账户处于「受限」，请先在黑名单管理解除限制，再调整账户状态')
    return
  }
  statusTarget.value = item
  statusTargetValue.value = item.account_status === '停用' ? '正常' : '停用'
  statusReason.value = ''
  statusError.value = ''
  statusDialogVisible.value = true
}

function closeStatusDialog(): void {
  statusDialogVisible.value = false
  statusTarget.value = null
  statusReason.value = ''
  statusError.value = ''
}

async function submitStatus(): Promise<void> {
  const target = statusTarget.value
  if (!target) return
  const reason = statusReason.value.trim()
  if (!reason) {
    statusError.value = '请填写原因（本次操作将记入审计日志）'
    return
  }
  statusSubmitting.value = true
  statusError.value = ''
  try {
    await updateUserAccountStatus(target.id, {
      account_status: statusTargetValue.value,
      reason,
    })
    ElMessage.success(
      `已${statusTargetValue.value === '停用' ? '停用' : '恢复'}账户「${target.name}」`,
    )
    closeStatusDialog()
    await refresh()
  } catch (caught) {
    statusError.value = toBookingFailure(caught).message
  } finally {
    statusSubmitting.value = false
  }
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
  statusDialogVisible,
  statusTarget,
  statusTargetValue,
  statusReason,
  statusSubmitting,
  statusError,
  openStatusDialog,
  closeStatusDialog,
  submitStatus,
}
}
