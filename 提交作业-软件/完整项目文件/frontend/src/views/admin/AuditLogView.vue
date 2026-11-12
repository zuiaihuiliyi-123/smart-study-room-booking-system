<script setup lang="ts">
/**
 * 审计日志查询（D2 / NFR-009）。
 *
 * 只读：管理员可查询关键操作与越权尝试，支持按操作类型、操作人、目标类型与
 * 操作日期筛选；不提供修改、删除或导出（FR-033 已排除）。
 *
 * 范围与保留期：
 * - 记录由后端 `audit_service.record` 只追加写入；
 * - 当前系统没有自动清理任务，实际保留时间由数据库运维策略决定；
 * - 页面只展示后端已记录的内容，不推断未记录的操作。
 */
import { onMounted, ref } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import FilterBar from '@/components/FilterBar.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import PageHeader from '@/components/PageHeader.vue'
import type { AuditLog } from '@/types'
import {
  operatorLabelOf,
  reservationLabelOf,
  roomNameOf,
  seatIdLabel,
  userLabelOf,
  type AdminDirectory,
} from '@/utils/adminData'
import { formatDateTime, isAfterToday } from '@/utils/format'
import { useAuditManage } from '@/utils/useAuditManage'

const {
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
} = useAuditManage()

const detailVisible = ref(false)
const detail = ref<AuditLog | null>(null)

const ACTION_OPTIONS: { value: string; label: string }[] = [
  { value: 'LOGIN_SUCCESS', label: '登录成功' },
  { value: 'LOGIN_FAILED', label: '登录失败' },
  { value: 'LOGIN_LOCKED', label: '登录锁定' },
  { value: 'REGISTER_SUCCESS', label: '注册成功' },
  { value: 'PASSWORD_CHANGED', label: '修改密码' },
  { value: 'UNAUTHORIZED_ATTEMPT', label: '越权尝试' },
  { value: 'ACCOUNT_STATUS_UPDATE', label: '账户状态变更' },
  { value: 'BLACKLIST_ADD', label: '加入黑名单' },
  { value: 'BLACKLIST_RELEASE', label: '解除黑名单' },
  { value: 'BLACKLIST_AUTO_RESTRICT', label: '自动限制' },
  { value: 'MANUAL_VIOLATION', label: '手动违约登记' },
  { value: 'RESERVATION_FORCE_CANCEL', label: '强制取消预约' },
  { value: 'ROOM_UPDATE', label: '修改自习室' },
  { value: 'ROOM_DELETE', label: '删除自习室' },
  { value: 'ROOM_TEMP_CLOSE', label: '临时关闭' },
  { value: 'ROOM_CLOSURE_RELEASE', label: '解除临时关闭' },
  { value: 'SEAT_STATUS_UPDATE', label: '修改座位状态' },
  { value: 'SEAT_STATUS_BATCH', label: '批量修改座位状态' },
  { value: 'COMPLAINT_HANDLE', label: '处理投诉' },
  { value: 'COMPLAINT_CONFIRM', label: '确认关闭投诉' },
]

const TARGET_OPTIONS: { value: string; label: string }[] = [
  { value: 'USER', label: '用户' },
  { value: 'SEAT', label: '座位' },
  { value: 'ROOM', label: '自习室' },
  { value: 'reservation', label: '预约单' },
  { value: 'COMPLAINT', label: '投诉' },
  { value: 'api', label: '接口' },
]

const ACTION_LABELS = new Map(ACTION_OPTIONS.map((item) => [item.value, item.label]))
const TARGET_LABELS = new Map(TARGET_OPTIONS.map((item) => [item.value, item.label]))

function actionLabel(value: string): string {
  return ACTION_LABELS.get(value) ?? value
}

function targetLabel(row: AuditLog): string {
  const id = row.target_id
  const type = TARGET_LABELS.get(row.target_type) ?? row.target_type
  if (id === null) return type
  if (row.target_type === 'USER') return userLabelOf(directory.value, id)
  if (row.target_type === 'SEAT') return seatIdLabel(directory.value, id)
  if (row.target_type === 'ROOM') return roomNameOf(directory.value, id)
  if (row.target_type === 'reservation') return reservationLabelOf(directory.value, id)
  return `${type} #${id}`
}

function openDetail(row: AuditLog): void {
  detail.value = row
  detailVisible.value = true
}

function hasChange(row: AuditLog): boolean {
  return Boolean(row.before_value || row.after_value)
}

function prettyValue(value: string | null): string {
  if (!value) return '—'
  try {
    return JSON.stringify(JSON.parse(value), null, 2)
  } catch {
    return value
  }
}

function disabledDate(value: Date): boolean {
  return isAfterToday(value)
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="审计日志"
      subtitle="查询关键操作与越权尝试；只读，不提供修改、删除或导出"
    >
      <template #actions>
        <el-button :loading="refreshing" @click="refresh()">刷新</el-button>
      </template>
    </PageHeader>

    <FilterBar :loading="loading" @search="onSearch" @reset="onReset">
      <label class="filter-field">
        <span class="filter-field__label">操作类型</span>
        <el-select v-model="actionType" class="w-180" clearable placeholder="全部类型">
          <el-option label="全部类型" value="" />
          <el-option
            v-for="item in ACTION_OPTIONS"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">操作人</span>
        <el-select
          v-model="operatorId"
          class="w-200"
          clearable
          filterable
          placeholder="全部操作人"
        >
          <el-option label="全部操作人" value="" />
          <el-option
            v-for="item in operatorOptions"
            :key="item.id"
            :label="item.label"
            :value="item.id"
          />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">目标类型</span>
        <el-select v-model="targetType" class="w-160" clearable placeholder="全部目标">
          <el-option label="全部目标" value="" />
          <el-option
            v-for="item in TARGET_OPTIONS"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">操作时间</span>
        <el-date-picker
          v-model="dateRange"
          class="w-260"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          :disabled-date="disabledDate"
        />
      </label>
    </FilterBar>

    <div class="admin-toolbar">
      <div class="admin-toolbar__buttons">
        <el-button :loading="refreshing" @click="refresh()">刷新</el-button>
      </div>
      <span class="admin-toolbar__hint">只读审计 · 共 {{ total }} 条记录</span>
    </div>

    <section class="ssr-card">
      <LoadingBlock v-if="loading" :rows="6" text="正在读取审计日志…" />

      <div v-else-if="errorMessage" class="panel">
        <el-alert type="error" :closable="false" show-icon title="审计日志读取失败">
          <p>{{ errorMessage }}</p>
        </el-alert>
        <el-button type="primary" plain @click="load">重试</el-button>
      </div>

      <EmptyState
        v-else-if="items.length === 0"
        description="当前筛选条件下没有审计记录。可放宽操作类型、操作人或时间范围"
      />

      <template v-else>
        <div class="table-wrap">
          <el-table :data="items" size="small" border style="min-width: 1180px">
            <el-table-column label="操作时间" width="160">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>

            <el-table-column label="操作人" min-width="170">
              <template #default="{ row }">
                {{ operatorLabelOf(directory, row.operator_id) }}
              </template>
            </el-table-column>

            <el-table-column label="操作类型" min-width="180">
              <template #default="{ row }">
                <div>{{ actionLabel(row.action_type) }}</div>
                <div class="ssr-text-muted code">{{ row.action_type }}</div>
              </template>
            </el-table-column>

            <el-table-column label="目标" min-width="230">
              <template #default="{ row }">{{ targetLabel(row) }}</template>
            </el-table-column>

            <el-table-column label="原因 / 说明" min-width="260" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.reason">{{ row.reason }}</span>
                <span v-else class="ssr-text-muted">—</span>
              </template>
            </el-table-column>

            <el-table-column label="变更" width="100">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openDetail(row)">
                  {{ hasChange(row) ? '查看变更' : '详情' }}
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div class="pager" role="navigation" aria-label="分页">
          <el-pagination
            background
            layout="total, sizes, prev, pager, next"
            :total="total"
            :current-page="page"
            :page-size="pageSize"
            :page-sizes="[20, 50, 100]"
            @current-change="onPageChange"
            @size-change="onPageSizeChange"
          />
        </div>
      </template>
    </section>

    <el-alert class="notice" type="info" :closable="false" show-icon title="关于审计日志">
      <p>
        审计日志由后端只追加写入；本页只读，不提供修改、删除或导出入口（FR-033 已排除）。
      </p>
      <p>
        当前系统没有自动清理任务，实际保留时间由数据库运维策略决定；查询范围包含登录、账户、资源、预约、违约、投诉、黑名单等关键操作与越权尝试。
      </p>
      <p>审计内容可能包含业务操作原因，请按最小必要范围使用。</p>
    </el-alert>

    <el-drawer v-model="detailVisible" title="审计详情" size="520px">
      <template v-if="detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="记录号">#{{ detail.id }}</el-descriptions-item>
          <el-descriptions-item label="操作时间">
            {{ formatDateTime(detail.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="操作人">
            {{ operatorLabelOf(directory, detail.operator_id) }}
          </el-descriptions-item>
          <el-descriptions-item label="操作类型">
            {{ actionLabel(detail.action_type) }}（{{ detail.action_type }}）
          </el-descriptions-item>
          <el-descriptions-item label="目标">{{ targetLabel(detail) }}</el-descriptions-item>
          <el-descriptions-item label="原因 / 说明">
            {{ detail.reason || '—' }}
          </el-descriptions-item>
        </el-descriptions>

        <section class="detail-block">
          <h4>变更前</h4>
          <pre class="detail-value">{{ prettyValue(detail.before_value) }}</pre>
        </section>
        <section class="detail-block">
          <h4>变更后</h4>
          <pre class="detail-value">{{ prettyValue(detail.after_value) }}</pre>
        </section>

        <p class="ssr-text-muted detail-note">
          审计记录只读；本抽屉仅展示数据库中的原始内容，不执行任何修改操作。
        </p>
      </template>
    </el-drawer>
  </div>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
}

.panel p {
  margin: 0;
}

.code {
  margin-top: 2px;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 11px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

.notice {
  margin-top: 12px;
}

.notice p {
  margin: 0 0 4px;
  font-size: var(--ssr-font-note);
  line-height: 1.6;
}

.notice p:last-child {
  margin-bottom: 0;
}

.detail-block {
  margin-top: 16px;
}

.detail-block h4 {
  margin: 0 0 6px;
  color: var(--ssr-ink);
  font-size: 13px;
  font-weight: 600;
}

.detail-value {
  max-height: 220px;
  padding: 10px 12px;
  margin: 0;
  overflow: auto;
  color: var(--ssr-ink);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--ssr-bg);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius-sm);
}

.detail-note {
  margin: 14px 0 0;
  line-height: 1.6;
}

.w-160 {
  width: 160px;
}

.w-180 {
  width: 180px;
}

.w-200 {
  width: 200px;
}

.w-260 {
  width: 260px;
}
</style>

