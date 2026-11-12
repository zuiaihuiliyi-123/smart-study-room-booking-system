<script setup lang="ts">
/**
 * 审计日志查询（D2 / NFR-009）。
 *
 * 只读：管理员可查询关键操作与越权尝试，支持按操作类型、操作人、目标类型与
 * 操作日期筛选；不提供修改、删除或导出（FR-033 已排除）。
 *
 * 页面只负责编排；筛选、表格与详情抽屉分别拆到
 * `components/admin/audit/`，操作类型/目标类型文案集中在 `utils/auditMeta.ts`。
 */
import { onMounted, ref } from 'vue'

import AuditLogDetailDrawer from '@/components/admin/audit/AuditLogDetailDrawer.vue'
import AuditLogFilters from '@/components/admin/audit/AuditLogFilters.vue'
import AuditLogTable from '@/components/admin/audit/AuditLogTable.vue'
import PageHeader from '@/components/PageHeader.vue'
import type { AuditLog } from '@/types'
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

function openDetail(row: AuditLog): void {
  detail.value = row
  detailVisible.value = true
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="page">
    <PageHeader title="审计日志" subtitle="查询关键操作与越权尝试；只读，不提供修改、删除或导出">
      <template #actions>
        <el-button :loading="refreshing" @click="refresh()">刷新</el-button>
      </template>
    </PageHeader>

    <AuditLogFilters
      v-model:action-type="actionType"
      v-model:operator-id="operatorId"
      v-model:target-type="targetType"
      v-model:date-range="dateRange"
      :loading="loading"
      :operator-options="operatorOptions"
      @search="onSearch"
      @reset="onReset"
    />

    <div class="admin-toolbar">
      <div class="admin-toolbar__buttons">
        <el-button :loading="refreshing" @click="refresh()">刷新</el-button>
      </div>
      <span class="admin-toolbar__hint">只读审计 · 共 {{ total }} 条记录</span>
    </div>

    <AuditLogTable
      :items="items"
      :loading="loading"
      :error-message="errorMessage"
      :total="total"
      :page="page"
      :page-size="pageSize"
      :directory="directory"
      @retry="load"
      @open-detail="openDetail"
      @page-change="onPageChange"
      @page-size-change="onPageSizeChange"
    />

    <el-alert class="notice" type="info" :closable="false" show-icon title="关于审计日志">
      <p>审计日志由后端只追加写入；本页只读，不提供修改、删除或导出入口（FR-033 已排除）。</p>
      <p>
        当前系统没有自动清理任务，实际保留时间由数据库运维策略决定；查询范围包含登录、账户、资源、预约、违约、投诉、黑名单等关键操作与越权尝试。
      </p>
      <p>审计内容可能包含业务操作原因，请按最小必要范围使用。</p>
    </el-alert>

    <AuditLogDetailDrawer v-model="detailVisible" :detail="detail" :directory="directory" />
  </div>
</template>

<style scoped>
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
</style>
