<script setup lang="ts">
import LoadingBlock from '@/components/LoadingBlock.vue'

withDefaults(
  defineProps<{
    label: string
    value: string | number
    unit?: string
    hint?: string
    tone?: 'primary' | 'success' | 'warning' | 'danger'
    loading?: boolean
    /** 数据截至时间等口径说明，见 AGENTS §4「10 秒是读取周期」 */
    footnote?: string
  }>(),
  { unit: '', hint: '', tone: 'primary', loading: false, footnote: '' },
)
</script>

<template>
  <section class="stat-card" :class="`stat-card--${tone}`">
    <p class="stat-card__label">{{ label }}</p>

    <LoadingBlock v-if="loading" :rows="1" text="读取中" />

    <template v-else>
      <p class="stat-card__value">
        <span class="stat-card__num">{{ value }}</span>
        <span v-if="unit" class="stat-card__unit">{{ unit }}</span>
      </p>
      <p v-if="hint" class="stat-card__hint">{{ hint }}</p>
    </template>

    <p v-if="footnote" class="stat-card__footnote">{{ footnote }}</p>
  </section>
</template>

<style scoped>
.stat-card {
  padding: 14px 16px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.stat-card__label {
  margin: 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

.stat-card__value {
  display: flex;
  gap: 4px;
  align-items: baseline;
  margin: 6px 0 0;
}

.stat-card__num {
  color: var(--ssr-primary);
  font-size: 24px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-card__unit {
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

.stat-card__hint {
  margin: 4px 0 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

.stat-card__footnote {
  margin: 8px 0 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

.stat-card--success .stat-card__num {
  color: var(--ssr-success);
}

.stat-card--warning .stat-card__num {
  color: var(--ssr-warning);
}

.stat-card--danger .stat-card__num {
  color: var(--ssr-danger);
}
</style>
