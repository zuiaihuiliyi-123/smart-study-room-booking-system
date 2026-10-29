<script setup lang="ts">
import { ref, watch } from 'vue'

import type { Reservation } from '@/types'
import { seatDisplayName, type SeatRef } from '@/utils/bookingData'
import { bracketRangeText } from '@/utils/bookingRules'

const props = defineProps<{
  /** 非 null 即打开对话框 */
  reservation: Reservation | null
  directory: Map<number, SeatRef> | null
  submitting: boolean
}>()

const emit = defineEmits<{
  (e: 'submit', payload: { score: number; content: string }): void
  (e: 'close'): void
}>()

const RATE_TEXTS = ['很差', '较差', '一般', '满意', '非常满意'] as const

const score = ref(0)
const content = ref('')
const touched = ref(false)

// 换一条预约单就重置草稿，避免把上一单的评分带到下一单（一单一评，BR-013）
watch(
  () => props.reservation?.id,
  () => {
    score.value = 0
    content.value = ''
    touched.value = false
  },
)

function onSubmit(): void {
  touched.value = true
  if (score.value < 1) return
  emit('submit', { score: score.value, content: content.value })
}
</script>

<template>
  <el-dialog
    :model-value="props.reservation !== null"
    title="评价本次使用"
    width="min(520px, 92vw)"
    :close-on-click-modal="false"
    @close="emit('close')"
  >
    <div v-if="props.reservation" class="review">
      <dl class="review__meta">
        <div>
          <dt>预约单</dt>
          <dd>#{{ props.reservation.id }}</dd>
        </div>
        <div>
          <dt>座位</dt>
          <dd>{{ seatDisplayName(props.directory, props.reservation.seat_id) }}</dd>
        </div>
        <div>
          <dt>时段</dt>
          <dd>
            {{ props.reservation.reserve_date }}
            {{ bracketRangeText(props.reservation.start_time, props.reservation.end_time) }}
          </dd>
        </div>
        <div>
          <dt>签退时间</dt>
          <dd>{{ props.reservation.check_out_time ?? '—' }}</dd>
        </div>
      </dl>

      <div class="review__field">
        <span class="review__label">总体评分（1～5 星，必填）</span>
        <el-rate v-model="score" :max="5" show-text :texts="[...RATE_TEXTS]" />
      </div>
      <p v-if="touched && score < 1" class="review__error">
        请选择 1～5 星评分：评分取值必须落在 1～5 区间（验收标准）
      </p>

      <div class="review__field">
        <span class="review__label">评价内容（选填，最多 500 字）</span>
        <el-input
          v-model="content"
          type="textarea"
          :rows="3"
          maxlength="500"
          show-word-limit
          placeholder="说说本次使用的体验，例如环境、座位与设备情况…"
        />
      </div>

      <p class="ssr-text-muted">
        评价对象为本次状态「已完成」的预约单，一单一评且提交后不可修改；评价不影响预约单状态与时段可预约性
        。
      </p>
    </div>

    <template #footer>
      <el-button @click="emit('close')">取消</el-button>
      <el-button type="primary" :loading="props.submitting" @click="onSubmit">提交评价</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.review {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.review__meta {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 8px 14px;
  padding: 10px 12px;
  margin: 0;
  background: var(--ssr-bg);
  border-radius: var(--ssr-radius-sm);
}

.review__meta div {
  display: flex;
  gap: 6px;
  align-items: baseline;
  min-width: 0;
}

.review__meta dt {
  flex: 0 0 auto;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

.review__meta dd {
  margin: 0;
  overflow: hidden;
  font-size: var(--ssr-font-note);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.review__field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.review__label {
  color: var(--ssr-ink);
  font-size: var(--ssr-font-note);
  font-weight: 600;
}

.review__error {
  margin: -6px 0 0;
  color: var(--ssr-danger);
  font-size: var(--ssr-font-note);
}
</style>
