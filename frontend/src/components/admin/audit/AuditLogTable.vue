<script setup lang="ts">
import EmptyState from '@/components/EmptyState.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import type { AuditLog } from '@/types'
import type { AdminDirectory } from '@/utils/adminData'
import { actionLabel, hasChange, targetLabel } from '@/utils/auditMeta'
import { operatorLabelOf } from '@/utils/adminData'
import { formatDateTime } from '@/utils/format'

const props = defineProps<{
  items: AuditLog[]
  loading: boolean
  errorMessage: string
  total: number
  page: number
  pageSize: number
  directory: AdminDirectory | null
}>()

const emit = defineEmits<{
  (e: 'retry'): void
  (e: 'open-detail', row: AuditLog): void
  (e: 'page-change', page: number): void
  (e: 'page-size-change', size: number): void
}>()

function onPageChange(value: number): void {
  emit('page-change', value)
}

function onPageSizeChange(value: number): void {
  emit('page-size-change', value)
}
</script>

<template>
  <section class="ssr-card">
    <LoadingBlock v-if="props.loading" :rows="6" text="正在读取审计日志…" />

    <div v-else-if="props.errorMessage" class="panel">
      <el-alert type="error" :closable="false" show-icon title="审计日志读取失败">
        <p>{{ props.errorMessage }}</p>
      </el-alert>
      <el-button type="primary" plain @click="emit('retry')">重试</el-button>
    </div>

    <EmptyState
      v-else-if="props.items.length === 0"
      description="当前筛选条件下没有审计记录。可放宽操作类型、操作人或时间范围"
    />

    <template v-else>
      <div class="table-wrap">
        <el-table :data="props.items" size="small" border style="min-width: 1180px">
          <el-table-column label="操作时间" width="160">
            <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
          </el-table-column>

          <el-table-column label="操作人" min-width="170">
            <template #default="{ row }">
              {{ operatorLabelOf(props.directory, row.operator_id) }}
            </template>
          </el-table-column>

          <el-table-column label="操作类型" min-width="180">
            <template #default="{ row }">
              <div>{{ actionLabel(row.action_type) }}</div>
              <div class="ssr-text-muted code">{{ row.action_type }}</div>
            </template>
          </el-table-column>

          <el-table-column label="目标" min-width="230">
            <template #default="{ row }">{{ targetLabel(props.directory, row) }}</template>
          </el-table-column>

          <el-table-column label="原因 / 说明" min-width="260" show-overflow-tooltip>
            <template #default="{ row }">
              <span v-if="row.reason">{{ row.reason }}</span>
              <span v-else class="ssr-text-muted">—</span>
            </template>
          </el-table-column>

          <el-table-column label="变更" width="100">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="emit('open-detail', row)">
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
          :total="props.total"
          :current-page="props.page"
          :page-size="props.pageSize"
          :page-sizes="[20, 50, 100]"
          @current-change="onPageChange"
          @size-change="onPageSizeChange"
        />
      </div>
    </template>
  </section>
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
</style>
