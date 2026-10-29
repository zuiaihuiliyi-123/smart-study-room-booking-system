<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import { TARGET_HINTS, TARGET_TYPES, type TargetType } from '@/components/complaints/complaintMeta'
import type { Reservation, Room } from '@/types'
import type { SeatRef } from '@/utils/bookingData'
import { bracketRangeText } from '@/utils/bookingRules'

const props = defineProps<{
  rooms: Room[]
  seats: SeatRef[]
  reservations: Reservation[]
  submitting: boolean
}>()

const emit = defineEmits<{
  (e: 'submit', payload: { target_type: TargetType; target_id: number; content: string }): void
}>()

const CONTENT_MAX = 500

const targetType = ref<TargetType>('座位')
const targetId = ref<number | undefined>(undefined)
const content = ref('')
const touched = ref(false)

interface TargetOption {
  value: number
  label: string
}

const seatOptions = computed<TargetOption[]>(() =>
    [...props.seats]
    .sort((left, right) =>
      left.roomName === right.roomName
      ? left.seatNo.localeCompare(right.seatNo)
      : left.roomName.localeCompare(right.roomName),
  )
    .map((seat) => ({ value: seat.seatId, label: `${seat.roomName} · ${seat.seatNo}` })),
)

const roomOptions = computed<TargetOption[]>(() =>
    props.rooms.map((room) => ({ value: room.id, label: `${room.name} · ${room.location}` })),
)

const seatMap = computed(() => new Map(props.seats.map((seat) => [seat.seatId, seat])))

function reservationLabel(item: Reservation): string {
  const seat = seatMap.value.get(item.seat_id)
  const seatText = seat ? `${seat.roomName} · ${seat.seatNo}` : `座位 #${item.seat_id}`
  return `#${item.id} · ${item.reserve_date} ${bracketRangeText(
    item.start_time,
    item.end_time,
  )} · ${seatText}`
  }

  const reservationOptions = computed<TargetOption[]>(() =>
      props.reservations.map((item) => ({ value: item.id, label: reservationLabel(item) })),
  )

  const options = computed<TargetOption[]>(() => {
    if (targetType.value === '座位') return seatOptions.value
    if (targetType.value === '自习室') return roomOptions.value
    if (targetType.value === '预约单') return reservationOptions.value
    return []
  })

// 换对象类型就清空标识，避免把「座位 12」当成「预约单 12」提交
watch(targetType, () => {
  targetId.value = undefined
  touched.value = false
})

const contentError = computed(() => {
  if (!touched.value) return ''
  if (content.value.trim() === '') return '投诉内容为必填项，不能为空'
  return ''
})

const targetError = computed(() => {
  if (!touched.value) return ''
  if (targetId.value === undefined || targetId.value <= 0) return '请选择 / 填写投诉对象标识'
  return ''
})

function onSubmit(): void {
  touched.value = true
  if (targetError.value || contentError.value) return
  if (targetId.value === undefined) return
  emit('submit', {
    target_type: targetType.value,
    target_id: targetId.value,
    content: content.value,
  })
content.value = ''
targetId.value = undefined
touched.value = false
}
</script>

<template>
  <section class="ssr-card form">
    <header class="ssr-card__head">
      <h3>提交投诉</h3>
      <span class="ssr-text-muted">提交后状态为「待处理」</span>
    </header>

    <el-form label-position="top" @submit.prevent>
      <el-form-item label="投诉对象类型" required>
        <el-select v-model="targetType" class="form__control">
          <el-option v-for="type in TARGET_TYPES" :key="type" :label="type" :value="type" />
        </el-select>
        <p class="ssr-text-muted form__hint">{{ TARGET_HINTS[targetType] }}</p>
      </el-form-item>

      <el-form-item label="投诉对象标识" required :error="targetError">
        <el-select
          v-if="targetType !== '用户'"
          v-model="targetId"
          class="form__control"
          filterable
          :placeholder="options.length === 0 ? '候选项加载失败，请稍后重试' : '请选择'"
          :disabled="options.length === 0"
        >
          <el-option
            v-for="option in options"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
        <el-input-number
          v-else
          v-model="targetId"
          class="form__control"
          :min="1"
          :step="1"
          controls-position="right"
          placeholder="对方的用户编号"
        />
      </el-form-item>

      <el-form-item label="投诉内容" required :error="contentError">
        <el-input
          v-model="content"
          type="textarea"
          :rows="5"
          :maxlength="CONTENT_MAX"
          show-word-limit
          placeholder="请描述问题现象、发生时间与位置，便于管理员核实…"
        />
      </el-form-item>
    </el-form>

    <div class="form__foot">
      <p class="ssr-text-muted form__note">
        约束：内容必填且不超过 {{ CONTENT_MAX }} 字；投诉由用户发起，管理员只在「投诉处理」中受理
        （权限要求）。处理时限为自提交起 3 个工作日。
      </p>
      <el-button type="primary" :loading="props.submitting" @click="onSubmit">
        {{ props.submitting ? '提交中' : '提交投诉' }}
      </el-button>
    </div>
  </section>
</template>

<style scoped>
.form__control {
  width: 100%;
}

.form__hint,
.form__note {
  margin: 4px 0 0;
  line-height: 1.6;
}

.form :deep(.el-form-item) {
  margin-bottom: 14px;
}

.form__foot {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid var(--ssr-line);
}

.form__note {
  flex: 1 1 240px;
  margin: 0;
}
</style>
