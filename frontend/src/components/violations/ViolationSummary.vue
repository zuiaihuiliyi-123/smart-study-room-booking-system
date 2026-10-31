<script setup lang="ts">
import { computed } from 'vue'
import { Warning } from '@element-plus/icons-vue'

import { BOOKING_RULES } from '@/utils/bookingRules'

const props = defineProps<{
  /** 累计有效违约次数 */
  count: number
  threshold: number
  percent: number
  progressStatus: 'success' | 'warning' | 'exception'
  tone: 'ok' | 'warn' | 'danger'
  accountStatus: string
  restricted: boolean
  disabled: boolean
  /** 预计解除时间；为空串表示后端未提供该字段 */
  restrictUntil: string
  remaining: number
}>()

const days = BOOKING_RULES.restrictionDays

const consequence = computed(() => {
  if (props.count >= props.threshold) {
    return `累计违约已达阈值 ${props.threshold} 次：账户被限制，期满（限制 ${days} 天）自动解除。`
  }
  if (props.tone === 'warn') {
    return `再发生 ${props.remaining} 次违约即达到阈值 ${props.threshold} 次，届时账户将被限制 ${days} 天。`
  }
  return `累计达到 ${props.threshold} 次有效违约将触发限制 ${days} 天，期满自动解除。`
})
</script>

<template>
  <section class="summary">
    <div class="summary__meter">
      <div class="summary__head">
        <span class="summary__title">累计违约次数</span>
        <span class="summary__count" :class="`is-${props.tone}`">
          {{ props.count }} / {{ props.threshold }}
        </span>
      </div>
      <el-progress
        :percentage="props.percent"
        :status="props.progressStatus"
        :stroke-width="14"
        :show-text="false"
        striped
      />
      <p class="summary__consequence">{{ consequence }}</p>
      <p class="ssr-text-muted">
        违约次数由有效违约记录累加得出；本版不提供违约申诉与记录撤销路径，次数不会回退。
      </p>
    </div>

    <el-alert
      v-if="props.restricted || props.disabled"
      class="summary__banner"
      type="error"
      :closable="false"
      show-icon
      > <template #title>
      <strong>{{ props.disabled ? '账户已停用' : '账户当前处于受限状态' }}</strong>
    </template>
    <div class="summary__banner-body">
      <p>
        {{
        props.disabled
        ? '停用账户无法登录与创建预约，须由管理员恢复账户。'
        : '受限期间不能创建新预约，但可正常登录并签到使用既有预约；名下已有的未来预约保持原状、不被自动取消。'
        }}
      </p>
      <p v-if="props.restricted">
        <span class="summary__label">预计解除时间：</span>
        <b v-if="props.restrictUntil">{{ props.restrictUntil }}</b>
        <span v-else>管理员手动限制，没有自动解除时间，须由管理员解除</span>
      </p>
      <p class="summary__label">
        限制口径：累计有效违约满 {{ props.threshold }} 次自动限制 7 天，期满自动解除。
      </p>
    </div>
  </el-alert>

  <div v-else class="summary__banner summary__banner--ok">
    <el-icon class="summary__ok-icon"><Warning /></el-icon>
    <span>
      账户状态：<b>{{ props.accountStatus }}</b>，当前不受限；如对违约记录有疑问，可通过「我的投诉」提交问题反馈
      （违约申诉已裁定排除，不提供入口）。
    </span>
  </div>
</section>
</template>

<style scoped>
.summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1.2fr);
  gap: 14px;
  margin-bottom: 16px;
}

.summary__meter,
.summary__banner {
  padding: 14px 16px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.summary__head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 10px;
}

.summary__title {
  font-size: 14px;
  font-weight: 600;
}

.summary__count {
  font-size: 18px;
  font-weight: 600;
}

.summary__count.is-ok {
  color: var(--ssr-success);
}

.summary__count.is-warn {
  color: var(--ssr-warning-ink);
}

.summary__count.is-danger {
  color: var(--ssr-danger);
}

.summary__consequence {
  margin: 10px 0 4px;
  font-size: var(--ssr-font-note);
  font-weight: 600;
}

.summary__banner {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.summary__banner-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary__banner-body p {
  margin: 0;
  font-size: var(--ssr-font-note);
  line-height: 1.65;
}

.summary__label {
  color: var(--ssr-muted-ink);
}

.summary__banner--ok {
  flex-direction: row;
  gap: 8px;
  align-items: flex-start;
  font-size: var(--ssr-font-note);
}

.summary__ok-icon {
  flex: 0 0 auto;
  margin-top: 2px;
  color: var(--ssr-warning);
  font-size: 16px;
}

@media (max-width: 1024px) {
  .summary {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
