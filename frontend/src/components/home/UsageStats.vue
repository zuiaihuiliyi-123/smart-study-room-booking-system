<script setup lang="ts">
import { computed } from 'vue'

import type { Reservation } from '@/types'
import { parseTimeToMinutes } from '@/utils/bookingRules'

/**
 * 首页右下角的「本周使用」小结。
 *
 * 首页左下是快捷入口，右下原本空着；这里用本周的预约次数、时长和累计预约次数
 * 把那一块补上。数字都从已加载的本人预约里算，不额外发请求。
 */
const props = defineProps<{
  /** 今天的日期（YYYY-MM-DD），用来推算本周一的日期范围 */
  today: string
  reservations: Reservation[]
  loading: boolean
}>()

/** 本周周一至今的日期列表（周一为一周之始） */
const weekDates = computed(() => {
  const start = new Date(`${props.today}T00:00:00`)
  const offset = (start.getDay() + 6) % 7
  const monday = new Date(start)
  monday.setDate(start.getDate() - offset)
  const dates: string[] = []
  for (let i = 0; i <= offset; i += 1) {
    const day = new Date(monday)
    day.setDate(monday.getDate() + i)
    const month = `${day.getMonth() + 1}`.padStart(2, '0')
    const date = `${day.getDate()}`.padStart(2, '0')
    dates.push(`${day.getFullYear()}-${month}-${date}`)
  }
  return dates
})

const weekReservations = computed(() => {
  const dates = new Set(weekDates.value)
  return props.reservations.filter(
    (item) => dates.has(item.reserve_date) && item.status !== '已取消',
  )
})

const weekMinutes = computed(() =>
  weekReservations.value.reduce((total, item) => {
    const start = parseTimeToMinutes(item.start_time)
    const end = parseTimeToMinutes(item.end_time)
    if (start === null || end === null || end <= start) return total
    return total + (end - start)
  }, 0),
)

const weekHours = computed(() => {
  const hours = weekMinutes.value / 60
  return Number.isInteger(hours) ? `${hours}` : hours.toFixed(1)
})

/** 累计预约次数（不含已取消），与本周数字并列，作为长期使用量的参照 */
const totalCount = computed(
  () => props.reservations.filter((item) => item.status !== '已取消').length,
)

const tiles = computed(() => [
  { key: 'count', value: props.loading ? '—' : `${weekReservations.value.length}`, unit: '次', label: '本周预约' },
  { key: 'hours', value: props.loading ? '—' : weekHours.value, unit: '小时', label: '本周时长' },
  { key: 'total', value: props.loading ? '—' : `${totalCount.value}`, unit: '次', label: '累计预约' },
])
</script>

<template>
  <section class="usage" aria-label="本周使用">
    <header class="usage__head">
      <h3>本周使用</h3>
      <span class="ssr-text-muted">周一至今天</span>
    </header>

    <ul class="usage__tiles">
      <li v-for="tile in tiles" :key="tile.key" class="usage__tile">
        <span class="usage__value">
          {{ tile.value }}<em>{{ tile.unit }}</em>
        </span>
        <span class="usage__label">{{ tile.label }}</span>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.usage {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.usage__head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--ssr-line);
}

.usage__head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.usage__tiles {
  display: grid;
  flex: 1 1 auto;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  align-items: center;
  padding: 0;
  margin: 0;
  list-style: none;
}

.usage__tile {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.usage__value {
  font-size: 20px;
  font-weight: 600;
  line-height: 1.2;
  color: var(--ssr-ink);
  font-variant-numeric: tabular-nums;
}

.usage__value em {
  margin-left: 2px;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  font-style: normal;
  font-weight: 500;
}

.usage__label {
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}
</style>
