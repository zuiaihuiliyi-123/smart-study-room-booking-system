<script setup lang="ts">

import EmptyState from '@/components/EmptyState.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import StatusTag from '@/components/StatusTag.vue'
import type { Violation } from '@/types'
import { formatDateTime } from '@/utils/format'

const props = defineProps<{
  items: Violation[]
  loading: boolean
  errorMessage: string
  focusId: number | null
  /** 关联预约的可读文案（含座位与时段） */
  reservationLabel: (reservationId: number) => string
  /** 登记人：系统自动 / 管理员 #id（不展示他人姓名，NFR-006） */
  operatorLabel: (item: Violation) => string
}>()

const emit = defineEmits<{ (e: 'retry'): void }>()

function rowClass(data: { row: Violation }): string {
  return props.focusId !== null && data.row.id === props.focusId ? 'ssr-row-focus' : ''
}
</script>

<template>
  <LoadingBlock v-if="props.loading" :rows="6" text="正在读取违约记录…" />

  <div v-else-if="props.errorMessage" class="panel">
    <el-alert type="error" :closable="false" show-icon title="违约记录读取失败">
      <p>{{ props.errorMessage }}</p>
    </el-alert>
    <el-button type="primary" plain @click="emit('retry')">重试</el-button>
  </div>

  <EmptyState
    v-else-if="props.items.length === 0"
    description="没有违约记录，请继续保持按时签到与签退"
  />

  <div v-else class="table-wrap">
    <el-table
      :data="props.items"
      :row-class-name="rowClass"
      style="min-width: 880px"
      border
      size="small"
    >
      <el-table-column label="违约时间" width="150">
        <template #default="{ row }">
          {{ formatDateTime(row.created_at) }}
        </template>
      </el-table-column>

      <el-table-column label="类型" width="100">
        <template #default="{ row }">
          <StatusTag kind="violation" :value="row.type" />
        </template>
      </el-table-column>

      <el-table-column label="原因" min-width="240">
        <template #default="{ row }">{{ row.reason }}</template>
      </el-table-column>

      <el-table-column label="关联预约" min-width="240">
        <template #default="{ row }">
          <router-link class="link" :to="`/student/reservations?focus=${row.reservation_id}`">
            {{ props.reservationLabel(row.reservation_id) }}
          </router-link>
        </template>
      </el-table-column>

      <el-table-column label="登记人" width="130">
        <template #default="{ row }">{{ props.operatorLabel(row) }}</template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
  padding: 14px 16px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.panel p {
  margin: 0;
}

.link {
  color: var(--ssr-primary);
}
</style>


