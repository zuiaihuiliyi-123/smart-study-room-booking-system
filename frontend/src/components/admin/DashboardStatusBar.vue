<script setup lang="ts">
/**
 * 看板顶部状态条（本轮任务：数据截至时间 / 自动刷新次数 / 下次刷新倒计时 / 手动刷新）。
 *
 * 只做展示与一个「立即刷新」事件，刷新机制全部在 `useDashboard.ts`：
 * 这里读到的 `countdown` 是父组件每秒递减的值，不自己起定时器（避免两个定时器各走各的）。
 */
withDefaults(
  defineProps<{
    /** 最后一次**成功**读取的时刻，已格式化为 HH:mm:ss */
    updatedText: string
    refreshCount: number
    countdown: number
    /** 数据读取周期文案，如 "10 秒" */
    cycleText: string
    inFlight?: boolean
    paused?: boolean
  }>(),
  { inFlight: false, paused: false },
)

const emit = defineEmits<{ (e: 'refresh'): void }>()
</script>

<template>
  <section class="dash-status ssr-card" aria-live="polite">
    <div class="dash-status__items">
      <span>数据截至时间 <b>{{ updatedText }}</b></span>
      <span>自动刷新 <b>{{ refreshCount }}</b> 次</span>
      <span>下次刷新倒计时 <b>{{ countdown }}</b> 秒</span>
      <span class="dash-status__cycle ssr-text-muted">数据读取周期 {{ cycleText }}</span>
      <span v-if="inFlight" class="ssr-text-muted">正在读取…</span>
      <span v-else-if="paused" class="ssr-text-muted">页面已隐藏，自动刷新已暂停</span>
    </div>
    <div class="dash-status__actions">
      <el-button type="primary" size="small" :loading="inFlight" @click="emit('refresh')">
        立即刷新
      </el-button>
    </div>
  </section>
</template>

<style scoped>
.dash-status {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  margin-bottom: 12px;
}

.dash-status__items {
  display: flex;
  flex-wrap: wrap;
  gap: 18px;
  align-items: center;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

.dash-status__items b {
  color: var(--ssr-ink);
  font-variant-numeric: tabular-nums;
}

.dash-status__cycle {
  padding-left: 18px;
  border-left: 1px solid var(--ssr-line);
}
</style>
