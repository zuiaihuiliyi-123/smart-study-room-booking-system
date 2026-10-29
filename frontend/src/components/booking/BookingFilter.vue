<script setup lang="ts">
import { computed } from 'vue'

import type { BookingFilters } from '@/components/booking/types'
import type { Room } from '@/types'
import { BOOKING_RULES, durationText, minutesToTimeText, parseTimeToMinutes, shortTime } from '@/utils/bookingRules'
import type { DateOption } from '@/utils/bookingRules'

/**
 * 左栏筛选面板。
 *
 * `filters` 由页面持有并**就地编辑**（表单绑定对象字段，不触发 prop 赋值告警）；
 * 点击「查询」才把当前值提交给页面重新取数，因此改动筛选不会清空其他条件与已选座位。
 */
const props = defineProps<{
  filters: BookingFilters
  rooms: Room[]
  dateOptions: DateOption[]
  seatTypes: string[]
  openTime: string
  closeTime: string
  /** 今天的最早可选开始时间（已过时刻不可选） */
  minStartTime: string
  loading: boolean
  /** 查询结果摘要，如「可约 24 / 30 座」 */
  hint: string
}>()

const emit = defineEmits<{
  (e: 'search'): void
  (e: 'reset'): void
  (e: 'room-change'): void
}>()

/** 结束时间上限：开始时间 + 4 小时，且不超过闭馆时间（BR-003）。 */
const maxEndTime = computed(() => {
  const start = parseTimeToMinutes(props.filters.startTime)
  const close = parseTimeToMinutes(props.closeTime) ?? 22 * 60
  if (start === null) return minutesToTimeText(close)
  return minutesToTimeText(Math.min(start + BOOKING_RULES.maxHours * 60, close))
})

const durationHint = computed(() => {
  const start = parseTimeToMinutes(props.filters.startTime)
  const end = parseTimeToMinutes(props.filters.endTime)
  if (start === null || end === null || end <= start) return '请选择开始与结束时间（结束须晚于开始）'
  return `本次时长 ${durationText(end - start)}，上限 ${BOOKING_RULES.maxHours} 小时`
})

/** 开始时间变化后，结束时间若越界则自动收敛到合法值，避免留下无效组合。 */
function onStartChange() {
  const start = parseTimeToMinutes(props.filters.startTime)
  if (start === null) return
  const close = parseTimeToMinutes(props.closeTime) ?? 22 * 60
  const end = parseTimeToMinutes(props.filters.endTime)
  const maxEnd = Math.min(start + BOOKING_RULES.maxHours * 60, close)
  if (end === null || end <= start || end > maxEnd) {
    props.filters.endTime = minutesToTimeText(Math.min(start + 120, maxEnd))
  }
}
</script>

<template>
  <aside class="booking-filter" aria-label="筛选条件">
    <el-form label-position="top" size="default" @submit.prevent>
      <el-form-item label="自习室">
        <el-select
          v-model="filters.roomId"
          class="booking-filter__full"
          placeholder="请选择自习室"
          @change="emit('room-change')"
        >
          <el-option
            v-for="room in props.rooms"
            :key="room.id"
            :label="`${room.name}（${room.location}）`"
            :value="room.id"
          />
        </el-select>
      </el-form-item>

      <el-form-item label="日期（今天起 7 天内）">
        <el-select v-model="filters.reserveDate" class="booking-filter__full">
          <el-option
            v-for="option in props.dateOptions"
            :key="option.value"
            :label="option.label"
            :value="option.value"
          />
        </el-select>
      </el-form-item>

      <div class="booking-filter__times">
        <el-form-item label="开始时间">
          <el-time-select
            v-model="filters.startTime"
            class="booking-filter__full"
            :start="props.openTime"
            :end="props.closeTime"
            :min-time="props.minStartTime"
            step="00:30"
            :editable="false"
            placeholder="开始"
            @change="onStartChange"
          />
        </el-form-item>

        <el-form-item label="结束时间">
          <el-time-select
            v-model="filters.endTime"
            class="booking-filter__full"
            :start="props.openTime"
            :end="props.closeTime"
            :min-time="filters.startTime || props.openTime"
            :max-time="maxEndTime"
            step="00:30"
            :editable="false"
            placeholder="结束"
          />
        </el-form-item>
      </div>

      <p class="booking-filter__note">
        {{ durationHint }}；区间按左闭右开 <code>[s, e)</code> 判定。
      </p>

      <el-form-item label="座位类型">
        <el-select
          v-model="filters.seatType"
          class="booking-filter__full"
          placeholder="全部类型"
          :clearable="false"
        >
          <el-option label="全部类型" value="" />
          <el-option
            v-for="type in props.seatTypes"
            :key="type"
            :label="type"
            :value="type"
          />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-checkbox v-model="filters.powerOnly">仅看有插座</el-checkbox>
      </el-form-item>

      <div class="booking-filter__actions">
        <el-button type="primary" :loading="props.loading" @click="emit('search')">
          查询可预约座位
        </el-button>
        <el-button @click="emit('reset')">重置</el-button>
      </div>

      <p v-if="props.hint" class="booking-filter__hint">{{ props.hint }}</p>

      <p class="booking-filter__note">
        开放时间 {{ shortTime(props.openTime) }}–{{ shortTime(props.closeTime) }}；最多提前
        {{ BOOKING_RULES.advanceDays }} 天，每人每日最多 {{ BOOKING_RULES.dailyLimit }} 条有效预约。
      </p>
    </el-form>
  </aside>
</template>

<style scoped>
.booking-filter {
  padding: 14px 16px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.booking-filter__full {
  width: 100%;
}

.booking-filter__times {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 0 12px;
}

/*
窄屏（≤1024px）筛选栏会变成整行宽，此时若让 el-form-item / el-select 的 min-content
撑开网格轨道，整张卡片就会溢出视口，结束时间被裁掉。这里显式允许子项收缩。
*/
.booking-filter__times > * {
  min-width: 0;
}

:deep(.el-form-item__content) {
  min-width: 0;
}

:deep(.el-select) {
  min-width: 0;
}

.booking-filter__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.booking-filter__note,
.booking-filter__hint {
  margin: 0 0 12px;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  line-height: 1.7;
}

.booking-filter__hint {
  margin: 10px 0 0;
  color: var(--ssr-primary);
  font-weight: 600;
}

.booking-filter__note code {
  padding: 0 3px;
  background: var(--ssr-primary-light);
  border-radius: 3px;
}

:deep(.el-form-item) {
  margin-bottom: 12px;
}
</style>
