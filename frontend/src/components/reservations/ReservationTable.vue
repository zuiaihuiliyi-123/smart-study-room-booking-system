<script setup lang="ts">

import EmptyState from '@/components/EmptyState.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import StatusTag from '@/components/StatusTag.vue'
import type { Reservation } from '@/types'
import { seatDisplayName, type SeatRef } from '@/utils/bookingData'
import { bracketRangeText } from '@/utils/bookingRules'
import { formatMonthDayTime } from '@/utils/format'
import type { ReservationGating } from '@/utils/useMyReservations'

const props = defineProps<{
  items: Reservation[]
  loading: boolean
  errorMessage: string
  emptyText: string
  directory: Map<number, SeatRef> | null
  reviewedIds: Set<number>
  actingId: number | null
  /** 从站内消息跳转过来时高亮的记录编号 */
  focusId: number | null
  gating: ReservationGating
}>()

const emit = defineEmits<{
  (e: 'checkin', item: Reservation): void
  (e: 'checkout', item: Reservation): void
  (e: 'cancel', item: Reservation): void
  (e: 'review', item: Reservation): void
  (e: 'retry'): void
}>()

function stamp(value: string | null): string {
  return value ? formatMonthDayTime(value) : '—'
}

function rowClass(data: { row: Reservation }): string {
  return props.focusId !== null && data.row.id === props.focusId ? 'ssr-row-focus' : ''
}
</script>

<template>
  <LoadingBlock v-if="props.loading" :rows="6" text="正在读取预约记录…" />

  <div v-else-if="props.errorMessage" class="panel">
    <el-alert type="error" :closable="false" show-icon title="预约记录读取失败">
      <p>{{ props.errorMessage }}</p>
    </el-alert>
    <el-button type="primary" plain @click="emit('retry')">重试</el-button>
  </div>

  <EmptyState v-else-if="props.items.length === 0" :description="props.emptyText" />

  <div v-else class="table-wrap">
    <el-table
      :data="props.items"
      :row-class-name="rowClass"
      style="min-width: 900px"
      border
      size="small"
    >
      <el-table-column label="预约日期" width="112">
        <template #default="{ row }">
          <div>{{ row.reserve_date }}</div>
          <div class="ssr-text-muted">#{{ row.id }}</div>
        </template>
      </el-table-column>

      <el-table-column label="时段（左闭右开）" width="140">
        <template #default="{ row }">{{ bracketRangeText(row.start_time, row.end_time) }}</template>
      </el-table-column>

      <el-table-column label="自习室 · 座位号" min-width="160">
        <template #default="{ row }">{{ seatDisplayName(props.directory, row.seat_id) }}</template>
      </el-table-column>

      <el-table-column label="状态" width="118">
        <template #default="{ row }">
          <el-tooltip
            v-if="row.cancel_reason"
            :content="`取消原因：${row.cancel_reason}（${stamp(row.cancel_time)}）`"
            placement="top"
          >
            <span><StatusTag kind="reservation" :value="row.status" /></span>
          </el-tooltip>
          <StatusTag v-else kind="reservation" :value="row.status" />
        </template>
      </el-table-column>

      <el-table-column label="签到 / 签退时间" width="132">
        <template #default="{ row }">
          <div>签到 {{ stamp(row.check_in_time) }}</div>
          <div>签退 {{ stamp(row.check_out_time) }}</div>
        </template>
      </el-table-column>

      <el-table-column label="操作" min-width="196" fixed="right">
        <template #default="{ row }">
          <div class="ops">
            <template v-if="row.status === '待使用'">
              <el-tooltip
                :content="props.gating.checkinTip(row)"
                :disabled="props.gating.canCheckIn(row)"
                placement="top"
              >
                <span>
                  <el-button
                    type="primary"
                    size="small"
                    :disabled="!props.gating.canCheckIn(row)"
                    :loading="props.actingId === row.id"
                    @click="emit('checkin', row)"
                  >
                    签到
                  </el-button>
                </span>
              </el-tooltip>

              <el-tooltip
                :content="props.gating.cancelTip(row)"
                :disabled="props.gating.canCancel(row)"
                placement="top"
              >
                <span>
                  <el-button
                    size="small"
                    :disabled="!props.gating.canCancel(row)"
                    :loading="props.actingId === row.id"
                    @click="emit('cancel', row)"
                  >
                    取消
                  </el-button>
                </span>
              </el-tooltip>
            </template>

            <el-button
              v-else-if="row.status === '使用中'"
              type="primary"
              size="small"
              :loading="props.actingId === row.id"
              @click="emit('checkout', row)"
            >
              签退
            </el-button>

            <el-tooltip
              v-else-if="row.status === '已完成'"
              content="仅「已完成且尚未评价」的预约可评价，一单一评"
              :disabled="!props.reviewedIds.has(row.id)"
              placement="top"
            >
              <span>
                <el-button
                  size="small"
                  :disabled="props.reviewedIds.has(row.id)"
                  @click="emit('review', row)"
                >
                  {{ props.reviewedIds.has(row.id) ? '已评价' : '评价' }}
                </el-button>
              </span>
            </el-tooltip>

            <span v-else class="ssr-text-muted">该状态无可用操作</span>
          </div>
        </template>
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

.ops {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
}
</style>


