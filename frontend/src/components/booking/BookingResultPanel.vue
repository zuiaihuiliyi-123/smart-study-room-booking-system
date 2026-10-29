<script setup lang="ts">
import SeatMatrix from '@/components/booking/SeatMatrix.vue'
import type { BookingFailure, MatrixCell, MatrixGroup } from '@/components/booking/types'
import EmptyState from '@/components/EmptyState.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import { restrictUntilText } from '@/utils/bookingRules'
import { computed } from 'vue'

const props = defineProps<{
  loading: boolean
  error: BookingFailure | null
  /** C4 / C6：整时段因本人原因不可约时不再展示座位矩阵 */
  userBlock: 'C4' | 'C6' | null
  blockedHint: string
  groups: MatrixGroup[]
  selectedSeatId: number | null
  summary: string
  hint: string
  freeCount: number
  visibleCount: number
}>()

const restrictText = computed(() =>
    restrictUntilText(props.error?.restrictUntil ?? '') || '服务端未返回解除时间',
)

const emit = defineEmits<{
  (e: 'retry'): void
  (e: 'alternative'): void
  (e: 'clear-seat-filter'): void
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

    <div v-else-if="props.userBlock" class="booking-result__panel">
      <el-alert type="warning" :closable="false" show-icon title="该时段暂不可预约">
        <p>{{ props.blockedHint }}</p>
        <p class="ssr-text-muted">
          判定项 {{ props.userBlock }} 属用户级条件，与具体座位无关，因此不再展示座位矩阵。
        </p>
      </el-alert>
      <EmptyState
        description="该时段没有可预约座位"
        action-text="替我改选一个时段"
        @action="emit('alternative')"
      />
    </div>

    <EmptyState
      v-else-if="props.groups.length === 0"
      description="当前筛选条件下没有座位"
      action-text="清空座位类型 / 插座筛选"
      @action="emit('clear-seat-filter')"
    />

    <template v-else>
      <el-alert
        v-if="props.freeCount === 0"
        class="booking-result__notice"
        type="warning"
        :closable="false"
        show-icon
        title="本时段没有可预约座位"
        :description="`已列出 ${props.visibleCount} 个座位的资源状态与该时段占用情况，可改选其它时段。`"
      />
      <p v-else class="ssr-text-muted booking-result__notice">
        点击座位查看规则校验结果并提交预约；鼠标悬停可看座位号、类型、有无插座与当前时段占用。
      </p>

      <SeatMatrix
        :groups="props.groups"
        :selected-seat-id="props.selectedSeatId"
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
  margin-bottom: 12px;
}

.booking-result__summary {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.booking-result__hint {
  color: var(--ssr-primary);
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
