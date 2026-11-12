<script setup lang="ts">
/**
 * 座位基本信息 + 时段摘要（从 SeatDetailDrawer 抽出，控制单文件行数）。
 *
 * 关键呈现口径（AGENTS.md §4）：**资源状态**（座位自身属性）与**时段占用**（某座位在某时段
 * 是否被有效预约的派生结论）必须分开显示，不合并成"座位状态：使用中"。
 */
import StatusTag from '@/components/StatusTag.vue'
import type { Room, Seat } from '@/types'
import { timeRangeText } from '@/utils/bookingRules'

defineProps<{
  seat: Seat
  room: Room | null
  areaTitle: string
  occupancyLabel: string
  reserveDate: string
  startTime: string
  endTime: string
  durationNote: string
}>()
</script>

<template>
  <section class="drawer-block">
    <h4 class="drawer-block__title">座位与时段</h4>
    <dl class="drawer-dl">
      <div>
        <dt>座位</dt>
        <dd>
          {{ room?.name ?? '—' }} · {{ seat.seat_no }}
          <span class="ssr-text-muted">（{{ areaTitle }}）</span>
        </dd>
      </div>
      <div>
        <dt>座位类型</dt>
        <dd>{{ seat.seat_type }}</dd>
      </div>
      <div>
        <dt>插座</dt>
        <dd>{{ seat.has_power ? '有插座' : '无插座' }}</dd>
      </div>
      <div>
        <dt>资源状态</dt>
        <dd><StatusTag kind="seat" :value="seat.status" /></dd>
      </div>
      <div>
        <dt>时段占用</dt>
        <dd>
          {{ occupancyLabel }}
        </dd>
      </div>
      <div>
        <dt>预约时段</dt>
        <dd>
          {{ reserveDate }} {{ timeRangeText(startTime, endTime) }}
          <span class="ssr-text-muted">（{{ durationNote }}）</span>
        </dd>
      </div>
    </dl>
  </section>
</template>

<style scoped>
.drawer-dl {
  margin: 0;
}

.drawer-dl > div {
  display: flex;
  gap: 10px;
  padding: 3px 0;
  font-size: var(--ssr-font-note);
}

.drawer-dl dt {
  flex: 0 0 72px;
  color: var(--ssr-muted-ink);
}

.drawer-dl dd {
  min-width: 0;
  margin: 0;
}

</style>
