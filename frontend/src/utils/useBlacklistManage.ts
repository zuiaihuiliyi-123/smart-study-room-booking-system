/**
 * 「黑名单管理」页状态机（FR-044 + BR-009 / BR-010 / BR-012 / BR-018）。
 *
 * 口径要点：
 * - 记录状态只有三种（SM-03 / ST-042）：**生效中 / 已解除 / 已过期**；
 * - 手动加入（ST-041）必填原因与期限，加入后账户转「受限」；
 * - 手动解除（ST-043）必填原因，记录操作者、时间与原因；
 * - **ST-042 例外**：若该账户存在**管理员手动设置**且仍生效的限制，系统**不得自动解除**——
 *   界面必须显式说明这一点（BR-010 / ST-042）；
 * - NFR-009：加入与解除都提示「本次操作将记入审计日志」并收集原因。
 */
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'

import { addBlacklist, listBlacklist, releaseBlacklist } from '@/api/blacklist'
import type { BlacklistEntry } from '@/types'
import { invalidateAdminDirectory, loadAdminDirectory, type AdminDirectory } from '@/utils/adminData'
import { toBookingFailure } from '@/utils/bookingData'
import { useAdminScope } from '@/utils/useAdminScope'

export type BlacklistStateFilter = '全部' | '生效中' | '已解除' | '已过期'
export type BlacklistModeFilter = '全部' | '自动' | '手动'

export function useBlacklistManage() {
  const scope = useAdminScope()

  const directory = ref<AdminDirectory | null>(null)
  const items = ref<BlacklistEntry[]>([])
  const total = ref(0)
  const loading = ref(true)
  const refreshing = ref(false)
  const errorMessage = ref('')

  const stateFilter = ref<BlacklistStateFilter>('生效中')
  const modeFilter = ref<BlacklistModeFilter>('全部')
  /** 从「用户管理」跳转过来时带上 user_id，作为唯一用户过滤条件（接口只支持 user_id） */
  const userId = ref<number | null>(null)
  const userIdLabel = ref('')
  const studentNoInput = ref('')
  const page = ref(1)
  const pageSize = ref(20)

  const addVisible = ref(false)
  const detailVisible = ref(false)
  const detail = ref<BlacklistEntry | null>(null)
  const submitting = ref(false)

  const filteredByUser = computed(() => userId.value !== null)

  async function load(): Promise<void> {
    loading.value = true
    errorMessage.value = ''
    try {
      const [result, dir] = await Promise.all([
        listBlacklist({
          page: page.value,
          page_size: pageSize.value,
          state: stateFilter.value === '全部' ? undefined : stateFilter.value,
          mode: modeFilter.value === '全部' ? undefined : modeFilter.value,
          user_id: userId.value ?? undefined,
        }),
      loadAdminDirectory().catch(() => null),
    ])
  items.value = result.items
  total.value = result.total
  directory.value = dir
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
  stateFilter.value = '生效中'
  modeFilter.value = '全部'
  userId.value = null
  userIdLabel.value = ''
  studentNoInput.value = ''
  page.value = 1
  void load()
}

/** 由「用户管理」跳转带入的过滤条件（`?user_id=&user_name=`） */
function applyQuery(query: Record<string, string>): void {
  const raw = query.user_id
  const parsed = raw === undefined ? Number.NaN : Number(raw)
  if (Number.isFinite(parsed) && parsed > 0) {
    userId.value = parsed
    userIdLabel.value = query.user_name ?? ''
    stateFilter.value = '全部'
  }
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

function openAdd(): void {
  addVisible.value = true
}

function openDetail(entry: BlacklistEntry): void {
  detail.value = entry
  detailVisible.value = true
}

/** 记录状态（SM-03 / ST-042）：已解除 → 已解除；未解除且未到期 → 生效中；其余 → 已过期 */
function stateOf(entry: BlacklistEntry): string {
  if (entry.released_at !== null) return '已解除'
  if (entry.expire_at === null) return '生效中'
  return new Date(entry.expire_at).getTime() > Date.now() ? '生效中' : '已过期'
}

function expireText(entry: BlacklistEntry): string {
  if (entry.expire_at === null) return '不设期限（仅可手动解除）'
  return entry.expire_at.replace('T', ' ').slice(0, 16)
}

/** 按学号定位用户：接口只接受 user_id，因此先用用户目录把学号翻译成 id */
function onSearchByStudentNo(): void {
  const text = studentNoInput.value.trim()
  if (text === '') {
    ElMessage.warning('请先输入学号')
    return
  }
  const found = directory.value?.usersByStudentNo.get(text)
  if (!found) {
    ElMessage.warning(`用户目录中没找到学号 ${text}：请确认学号是否正确，或先在「用户管理」确认该用户存在`)
    return
  }
  userId.value = found.id
  userIdLabel.value = found.name
  stateFilter.value = '全部'
  page.value = 1
  void load()
}

/** ST-041：手动加入黑名单（必填原因 + 期限） */
async function add(payload: {
  user_id: number
  reason: string
  expire_at: string | null
}): Promise<boolean> {
  if (payload.reason.trim() === '') {
    ElMessage.warning('请填写限制原因：原因会写入审计日志')
    return false
  }
  const user = directory.value?.usersById.get(payload.user_id)
  try {
    await ElMessageBox.confirm(
      `将用户 ${user ? `${user.name}（${user.student_no}）` : `#${payload.user_id}`} 加入黑名单，账户转为「受限」。限制期限：${payload.expire_at === null ? '不设期限（须管理员手动解除）' : payload.expire_at.replace('T', ' ')}。本次操作将记入审计日志，确认执行？`,
      '确认：手动加入黑名单',
      { type: 'warning', confirmButtonText: '确认加入', cancelButtonText: '返回检查' },
    )
  } catch {
    return false
  }
  submitting.value = true
  try {
    await addBlacklist({
      user_id: payload.user_id,
      reason: payload.reason.trim(),
      expire_at: payload.expire_at,
    })
  ElMessage.success('已加入黑名单，账户状态转为「受限」，并已发送站内消息告知用户')
  invalidateAdminDirectory()
  addVisible.value = false
  await refresh()
  return true
} catch (caught) {
  ElMessage.error(toBookingFailure(caught).message)
  return false
} finally {
  submitting.value = false
}
}

/** ST-043：手动解除（必填解除原因） */
async function release(reason: string): Promise<boolean> {
  const target = detail.value
  if (target === null) return false
  if (target.released_at !== null) {
    ElMessage.warning('该限制已解除，无需重复操作')
    return false
  }
  if (reason.trim() === '') {
    ElMessage.warning('请填写解除原因：原因会写入审计日志')
    return false
  }
  try {
    await ElMessageBox.confirm(
      `将解除黑名单记录 #${target.id}（用户 ${target.user_id}）。解除后若该账户不存在其它生效中的限制，账户恢复「正常」。本次操作将记入审计日志，确认执行？`,
      '确认：手动解除限制',
      { type: 'warning', confirmButtonText: '确认解除', cancelButtonText: '返回检查' },
    )
  } catch {
    return false
  }
  submitting.value = true
  try {
    const updated = await releaseBlacklist(target.id, { reason: reason.trim() })
    ElMessage.success('已解除该限制，并已发送站内消息告知用户')
    invalidateAdminDirectory()
    await refresh()
    // 解除后该记录通常不再属于当前筛选（默认只看「生效中」），仍保留这条最新快照，
    // 让管理员能在抽屉里看到解除时间、解除原因与解除人，而不是一个空白抽屉。
    detail.value = updated
    return true
  } catch (caught) {
    ElMessage.error(toBookingFailure(caught).message)
    return false
  } finally {
    submitting.value = false
  }
}

return {
  scopeLabel: scope.scopeLabel,
  directory,
  items,
  total,
  loading,
  refreshing,
  errorMessage,
  stateFilter,
  modeFilter,
  userId,
  userIdLabel,
  studentNoInput,
  filteredByUser,
  page,
  pageSize,
  addVisible,
  detailVisible,
  detail,
  submitting,
  load,
  refresh,
  onSearch,
  onReset,
  applyQuery,
  onPageChange,
  onPageSizeChange,
  openAdd,
  openDetail,
  onSearchByStudentNo,
  add,
  release,
  stateOf,
  expireText,
}
}
