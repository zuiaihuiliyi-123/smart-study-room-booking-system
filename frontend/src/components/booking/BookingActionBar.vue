<script setup lang="ts">
import type { Seat } from '@/types'

/**
 * 底部操作条：显示当前选中的座位与时段，右侧是确认入口。
 *
 * 整条吸附在内容底部，选座时不用再回到页面顶部找按钮。
 */
const props = defineProps<{
  seat: Seat | null
  dateText: string
  timeText: string
  /** 该座位在你所选时段的状态说明 */
  stateText: string
  /** 本人在该时段已有预约等整段不可约的原因 */
  blockedText: string
  blocked: boolean
}>()

const emit = defineEmits<{
  (e: 'confirm'): void
  (e: 'alternative'): void
}>()
</script>

<template>
  <footer class="action-bar">
    <div class="action-bar__info">
      <template v-if="props.blocked">
        <span class="action-bar__muted">{{ props.blockedText }}</span>
      </template>
      <template v-else-if="props.seat">
        <span class="action-bar__label">已选</span>
        <span class="action-bar__seat">{{ props.seat.seat_no }}</span>
        <span class="action-bar__muted">{{ props.stateText }}</span>
        <span class="action-bar__divider" aria-hidden="true"></span>
        <span class="action-bar__when">{{ props.dateText }} {{ props.timeText }}</span>
      </template>
      <span v-else class="action-bar__muted">点座位查看该时段能不能约</span>
    </div>

    <div class="action-bar__actions">
      <el-button v-if="props.blocked" @click="emit('alternative')">替我改选时段</el-button>
      <el-button
        type="primary"
        size="large"
        :disabled="!props.seat || props.blocked"
        @click="emit('confirm')"
      >
        确认预约
      </el-button>
    </div>
  </footer>
</template>

<style scoped>
.action-bar {
  display: flex;
  position: sticky;
  bottom: 0;
  z-index: 4;
  flex-wrap: wrap;
  gap: 10px 16px;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  margin-top: 12px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
  box-shadow: var(--ssr-shadow-md);
}

.action-bar__info {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  min-height: 32px;
  font-size: var(--ssr-font-note);
}

.action-bar__label,
.action-bar__muted {
  color: var(--ssr-muted-ink);
}

.action-bar__seat {
  padding: 2px 12px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--ssr-primary-ink);
  background: var(--ssr-primary-light);
  border-radius: 6px;
}

.action-bar__divider {
  width: 1px;
  height: 14px;
  background: var(--ssr-line);
}

.action-bar__when {
  color: var(--ssr-ink);
  font-variant-numeric: tabular-nums;
}

.action-bar__actions {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-left: auto;
}
</style>
