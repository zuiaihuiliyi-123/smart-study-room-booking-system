<script setup lang="ts">
/**
 * 预约单简表：用于「影响清单 / 冲突清单 / 详情抽屉里的关联预约」等只读场景。
 *
 * 为什么不直接用 el-table 在各页面各写一遍：BR-019 / BR-022 要求多处展示同一份
 * 受影响预约清单（临时关闭、座位状态调整、预约详情），列与口径必须完全一致，
 * 因此收敛为一个组件，避免各页面出现「有的列表没有状态列」这类不一致。
 */
import EmptyState from '@/components/EmptyState.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import StatusTag from '@/components/StatusTag.vue'
import type { Reservation } from '@/types'
import {
  seatIdLabel,
  studentNoOf,
  userLabelOf,
  type AdminDirectory,
} from '@/utils/adminData'
import { bracketRangeText } from '@/utils/bookingRules'

const props = withDefaults(
  defineProps<{
    items: Reservation[]
    loading?: boolean
    errorMessage?: string
    directory: AdminDirectory | null
    emptyText?: string
    /** 是否允许点击行（父级需要打开详情时开启） */
    clickable?: boolean
    maxHeight?: string
  }>(),
  { loading: false, errorMessage: '', emptyText: '没有受影响的预约', clickable: false, maxHeight: '320px' },
)

const emit = defineEmits<{
  (e: 'retry'): void
  (e: 'select', item: Reservation): void
}>()

function onRowClick(row: Reservation): void {
  if (!props.clickable) return
  emit('select', row)
}
</script>

<template>
  <div class="brief">
    <LoadingBlock v-if="loading" :rows="3" text="正在读取预约单…" />

    <div v-else-if="errorMessage" class="brief__error">
      <el-alert type="error" :closable="false" show-icon title="预约单读取失败">
        <p>{{ errorMessage }}</p>
      </el-alert>
      <el-button type="primary" plain size="small" @click="emit('retry')">重试</el-button>
    </div>

    <EmptyState v-else-if="items.length === 0" :description="emptyText" :image-size="60" />

    <div v-else class="table-wrap">
      <el-table
        :data="items"
        size="small"
        border
        :max-height="maxHeight"
        style="min-width: 760px"
        :row-style="clickable ? { cursor: 'pointer' } : undefined"
        @row-click="onRowClick"
      >
        <el-table-column label="预约单号" width="96">
          <template #default="{ row }">#{{ row.id }}</template>
        </el-table-column>

        <el-table-column label="预约日期" width="112" prop="reserve_date" />

        <el-table-column label="时段（左闭右开）" width="132">
          <template #default="{ row }">
            {{ bracketRangeText(row.start_time, row.end_time) }}
          </template>
        </el-table-column>

        <el-table-column label="自习室 · 座位号" min-width="170">
          <template #default="{ row }">{{ seatIdLabel(directory, row.seat_id) }}</template>
        </el-table-column>

        <el-table-column label="使用人" min-width="170">
          <template #default="{ row }">
            {{ userLabelOf(directory, row.user_id) }}
            <span class="ssr-text-muted">学号 {{ studentNoOf(directory, row.user_id) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="96">
          <template #default="{ row }">
            <StatusTag kind="reservation" :value="row.status" />
          </template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.brief {
  min-width: 0;
}

.brief__error {
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
}

.brief__error p {
  margin: 0;
}
</style>
