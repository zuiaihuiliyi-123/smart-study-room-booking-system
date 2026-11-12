<script setup lang="ts">
/**
 * 首页首次使用引导卡（C1）。
 *
 * 只在「本人没有任何预约记录」时由 HomeView 展示，关闭后按学号写入 localStorage，
 * 之后不再自动出现。规则数字全部取自 `BOOKING_RULES`，不在组件里硬编码，
 * 避免后端参数调整后页面文案与真实校验脱节。
 */
import { BOOKING_RULES } from '@/utils/bookingRules'

defineEmits<{
  (e: 'dismiss'): void
  (e: 'booking'): void
}>()

const rules = [
  {
    title: `最多提前 ${BOOKING_RULES.advanceDays} 天`,
    detail: `可选日期只到今天起第 ${BOOKING_RULES.advanceDays} 天，更远的日期不会出现在筛选里。`,
  },
  {
    title: `单次最长 ${BOOKING_RULES.maxHours} 小时`,
    detail: `时段按 ${BOOKING_RULES.granularity} 分钟为一格，同一时段不能重复占用。`,
  },
  {
    title: `每人每天最多 ${BOOKING_RULES.dailyLimit} 条有效预约`,
    detail: '有效预约指「待使用」或「使用中」；已完成、已取消、已违约不占用次数。',
  },
]
</script>

<template>
  <section class="guide ssr-card" aria-labelledby="first-use-guide-title">
    <header class="guide__head">
      <div>
        <span class="guide__eyebrow">首次使用</span>
        <h3 id="first-use-guide-title">预约前先记住这 {{ rules.length }} 条规则</h3>
      </div>
      <el-button link type="primary" @click="$emit('dismiss')">关闭</el-button>
    </header>

    <ul class="guide__rules">
      <li v-for="(rule, index) in rules" :key="rule.title" class="guide__rule">
        <span class="guide__index" aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}</span>
        <div class="guide__text">
          <b>{{ rule.title }}</b>
          <p>{{ rule.detail }}</p>
        </div>
      </li>
    </ul>

    <p class="guide__foot ssr-text-muted">
      签到窗口为开始前 {{ BOOKING_RULES.checkinEarly }} 分钟至开始后
      {{ BOOKING_RULES.checkinLate }} 分钟；距开始不足
      {{ BOOKING_RULES.cancelBefore }} 分钟时不能自行取消，该情形不计违约。
    </p>

    <div class="guide__actions">
      <el-button type="primary" @click="$emit('booking')">去预约座位</el-button>
      <span class="ssr-text-muted">关闭后不再自动出现；规则以服务端校验结果为准。</span>
    </div>
  </section>
</template>

<style scoped>
.guide {
  margin-bottom: 16px;
}

.guide__head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: flex-start;
  justify-content: space-between;
}

.guide__eyebrow {
  display: inline-block;
  padding: 1px 8px;
  margin-bottom: 6px;
  color: var(--ssr-primary-ink);
  font-size: 11.5px;
  font-weight: 600;
  background: var(--ssr-primary-light);
  border-radius: 999px;
}

.guide__head h3 {
  margin: 0;
  color: var(--ssr-ink);
  font-size: 17px;
  font-weight: 600;
}

.guide__rules {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px 18px;
  padding: 0;
  margin: 16px 0 0;
  list-style: none;
}

.guide__rule {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  min-width: 0;
}

.guide__index {
  flex: 0 0 auto;
  color: var(--ssr-primary-ink);
  font-size: 12px;
  font-weight: 700;
  line-height: 1.6;
  letter-spacing: 0.4px;
}

.guide__text {
  min-width: 0;
}

.guide__text b {
  display: block;
  color: var(--ssr-ink);
  font-size: 14px;
  font-weight: 600;
}

.guide__text p {
  margin: 3px 0 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  line-height: 1.6;
}

.guide__foot {
  padding-top: 12px;
  margin: 14px 0 0;
  font-size: var(--ssr-font-note);
  line-height: 1.7;
  border-top: 1px solid var(--ssr-line);
}

.guide__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
  align-items: center;
  margin-top: 12px;
}
</style>
