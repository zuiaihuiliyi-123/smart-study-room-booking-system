<script setup lang="ts">
import { computed } from 'vue'

import SeatMapCanvas from '@/components/booking/SeatMapCanvas.vue'
import type { BookingFailure, MatrixCell, MatrixGroup } from '@/components/booking/types'
import EmptyState from '@/components/EmptyState.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import type { Area } from '@/types'
import { restrictUntilText } from '@/utils/bookingRules'

const props = defineProps<{
  loading: boolean
  error: BookingFailure | null
  groups: MatrixGroup[]
  selectedSeatId: number | null
  /** 我在当前时段已占的座位 */
  mineIds?: readonly number[]
  summary: string
  hint: string
  freeCount: number
  visibleCount: number
  /** 这间自习室还没录入座位 */
  roomEmpty?: boolean
  /** 系统里还没有任何可预约的自习室 */
  noRoom?: boolean
  /** 当前自习室的分区名称；只读展示用，接口失败时地图用座位号前缀兜底 */
  areas?: readonly Area[]
  /** 所选时段已经开始：地图仍显示占用，但不能提交 */
  slotStarted?: boolean
}>()

const restrictText = computed(() =>
  restrictUntilText(props.error?.restrictUntil ?? '') || '管理员手动限制，须由管理员解除',
)

const emit = defineEmits<{
  (e: 'retry'): void
  (e: 'clear-seat-filter'): void
  (e: 'switch-room'): void
  (e: 'select', cell: MatrixCell): void
}>()
</script>

<template>
  <section class="booking-result" aria-label="可预约座位结果">
    <header class="booking-result__head">
      <p class="booking-result__summary">{{ props.summary }}</p>
      <span v-if="props.hint" class="booking-result__hint">{{ props.hint }}</span>
    </header>

    <LoadingBlock
      v-if="props.loading"
      :rows="8"
      min-height="320px"
      text="正在查询该时段的可预约座位…"
    />

    <div v-else-if="props.error" class="booking-result__panel">
      <el-alert
        type="error"
        :closable="false"
        show-icon
        :title="props.error.kind === 'restricted' ? '账户受限，暂不可预约' : '查询失败'"
      >
        <p>{{ props.error.message }}</p>
        <p v-if="props.error.kind === 'restricted'" class="ssr-text-muted">
          预计解除时间：{{ restrictText }}
        </p>
      </el-alert>
      <el-button class="booking-result__action" type="primary" plain @click="emit('retry')">
        重试
      </el-button>
    </div>

    <EmptyState
      v-else-if="props.noRoom"
      description="当前还没有可预约的自习室"
      action-text="刷新看看"
      @action="emit('retry')"
    />

    <EmptyState
      v-else-if="props.roomEmpty"
      description="这间自习室还没有座位，换一间试试"
      action-text="换一间自习室"
      @action="emit('switch-room')"
    />

    <EmptyState
      v-else-if="props.groups.length === 0 || props.visibleCount === 0"
      description="当前筛选条件下没有座位"
      action-text="清空座位类型 / 靠窗 / 插座筛选"
      @action="emit('clear-seat-filter')"
    />

    <template v-else>
      <el-alert
        v-if="props.slotStarted"
        class="booking-result__notice"
        type="info"
        :closable="false"
        show-icon
        title="该时段已开始，当前为只读查看"
        description="地图仍显示这个时段的座位占用；要提交预约，请选择尚未开始的时段。"
      />

      <el-alert
        v-else-if="props.freeCount === 0"
        class="booking-result__notice"
        type="warning"
        :closable="false"
        show-icon
        title="本时段没有可预约座位"
        :description="`已列出 ${props.visibleCount} 个符合筛选的座位，可改选其它时段。`"
      />

      <SeatMapCanvas
        :groups="props.groups"
        :selected-seat-id="props.selectedSeatId"
        :mine-ids="props.mineIds"
        :areas="props.areas"
        @select="emit('select', $event)"
      />
    </template>
  </section>
</template>

<style scoped>
.booking-result {
  min-width: 0;
}

.booking-result__head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}

.booking-result__summary {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.booking-result__hint {
  color: var(--ssr-primary-ink);
  font-size: var(--ssr-font-note);
  font-weight: 600;
}

.booking-result__panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-start;
}

.booking-result__action {
  align-self: flex-start;
}

.booking-result__notice {
  margin-bottom: 12px;
}
</style>
