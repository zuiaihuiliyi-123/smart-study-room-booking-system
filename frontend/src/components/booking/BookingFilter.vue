<script setup lang="ts">
import { Refresh } from '@element-plus/icons-vue'
import { computed } from 'vue'

import RoomStrip from '@/components/booking/RoomStrip.vue'
import type { BookingFilters } from '@/components/booking/types'
import type { Room } from '@/types'
import { BOOKING_RULES, durationText, minutesToTimeText, parseTimeToMinutes } from '@/utils/bookingRules'
import type { DateOption } from '@/utils/bookingRules'

/**
 * 顶部工具条：日期 / 自习室 / 时段 / 筛选。
 *
 * `filters` 由页面持有并**就地编辑**；改动日期、自习室或时间都会自动重新取数，
 * 「刷新」只是手动兜底。
 */
const props = defineProps<{
  filters: BookingFilters
  rooms: Room[]
  dateOptions: DateOption[]
  seatTypes: string[]
  openTime: string
  closeTime: string
  /** 时间选择下限；当前为开放时间，允许回看已开始的只读时段 */
  minStartTime: string
  loading: boolean
}>()

const emit = defineEmits<{
  (e: 'search'): void
  (e: 'reset'): void
  (e: 'room-change'): void
  (e: 'date-change'): void
}>()

/** 日期条：上面一行写「今天/明天/后天」或周几，下面一行写具体日期，八档宽度一致 */
const dateChips = computed(() =>
  props.dateOptions.map((option) => {
    const [head, rest] = option.label.includes(' · ') ? option.label.split(' · ') : ['', option.label]
    if (head) {
      const [date] = rest.split(' ')
      return { value: option.value, top: head, sub: date ?? '' }
    }
    const [date, weekday] = rest.split(' ')
    return { value: option.value, top: weekday ?? rest, sub: date ?? '' }
  }),
)

const maxEndTime = computed(() => {
  const start = parseTimeToMinutes(props.filters.startTime)
  const close = parseTimeToMinutes(props.closeTime) ?? 22 * 60
  if (start === null) return minutesToTimeText(close)
  return minutesToTimeText(Math.min(start + BOOKING_RULES.maxHours * 60, close))
})

const durationHint = computed(() => {
  const start = parseTimeToMinutes(props.filters.startTime)
  const end = parseTimeToMinutes(props.filters.endTime)
  if (start === null || end === null || end <= start) return '结束时间需要晚于开始时间'
  return `本次 ${durationText(end - start)}`
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

function pickDate(value: string) {
  if (props.filters.reserveDate === value) return
  props.filters.reserveDate = value
  emit('date-change')
}

function pickRoom(id: number) {
  if (props.filters.roomId === id) return
  props.filters.roomId = id
  emit('room-change')
}
</script>

<template>
  <section class="booking-bar" aria-label="筛选条件">
    <div class="date-strip" role="group" aria-label="预约日期">
      <button
        v-for="chip in dateChips"
        :key="chip.value"
        type="button"
        class="date-chip"
        :class="{ 'date-chip--on': props.filters.reserveDate === chip.value }"
        @click="pickDate(chip.value)"
      >
        <span class="date-chip__top">{{ chip.top }}</span>
        <span class="date-chip__sub">{{ chip.sub }}</span>
      </button>
    </div>

    <div class="bar-row">
      <RoomStrip :rooms="props.rooms" :room-id="props.filters.roomId" @change="pickRoom" />

      <div class="time-range">
        <el-time-select
          v-model="props.filters.startTime"
          class="time-control"
          :start="props.openTime"
          :end="props.closeTime"
          :min-time="props.minStartTime"
          step="00:05"
          :editable="false"
          :clearable="false"
          placeholder="开始"
          @change="onStartChange"
        />
        <span class="time-dash">–</span>
        <el-time-select
          v-model="props.filters.endTime"
          class="time-control"
          :start="props.openTime"
          :end="props.closeTime"
          :min-time="props.filters.startTime || props.openTime"
          :max-time="maxEndTime"
          step="00:05"
          :editable="false"
          :clearable="false"
          placeholder="结束"
        />
        <span class="time-note">{{ durationHint }}</span>
      </div>

      <label v-if="props.seatTypes.length > 1" class="type-select">
        <el-select v-model="props.filters.seatType" class="time-control" :clearable="false">
          <el-option label="全部类型" value="" />
          <el-option v-for="type in props.seatTypes" :key="type" :label="type" :value="type" />
        </el-select>
      </label>

      <div class="toggles">
        <el-checkbox v-model="props.filters.powerOnly">有插座</el-checkbox>
        <el-checkbox v-model="props.filters.windowOnly">靠窗</el-checkbox>
      </div>

      <div class="bar-actions">
        <el-button :icon="Refresh" :loading="props.loading" @click="emit('search')">刷新</el-button>
        <el-button text @click="emit('reset')">重置</el-button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.booking-bar {
  padding: 10px 14px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.date-strip {
  display: flex;
  gap: 8px;
  padding-bottom: 2px;
  overflow-x: auto;
  scrollbar-width: thin;
}

.date-chip {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 1px;
  align-items: center;
  min-width: 70px;
  padding: 5px 10px;
  font: inherit;
  color: var(--ssr-ink);
  cursor: pointer;
  background: var(--ssr-bg);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius-sm);
  transition:
    border-color 0.15s ease,
    background-color 0.15s ease;
}

.date-chip:hover {
  border-color: var(--ssr-primary);
}

.date-chip--on {
  color: var(--ssr-primary-ink);
  background: var(--ssr-primary-light);
  border-color: var(--ssr-primary);
}

.date-chip__top {
  font-size: var(--ssr-font-note);
  font-weight: 600;
  line-height: 1.3;
}

.date-chip__sub {
  font-size: calc(var(--ssr-font-note) - 1px);
  color: var(--ssr-muted-ink);
  font-variant-numeric: tabular-nums;
}

.date-chip--on .date-chip__sub {
  color: var(--ssr-primary-ink);
  opacity: 0.8;
}

.bar-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 14px;
  align-items: center;
  padding-top: 8px;
  margin-top: 8px;
  border-top: 1px solid var(--ssr-line);
}


.time-range {
  display: flex;
  gap: 6px;
  align-items: center;
}

.time-control {
  width: 104px;
}

.time-dash {
  color: var(--ssr-muted-ink);
}

.time-note {
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

.toggles {
  display: flex;
  gap: 12px;
  align-items: center;
}

.bar-actions {
  display: flex;
  gap: 6px;
  margin-left: auto;
}
</style>
