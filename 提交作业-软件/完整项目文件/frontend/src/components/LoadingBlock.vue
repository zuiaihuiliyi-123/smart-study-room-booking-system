<script setup lang="ts">
withDefaults(
  defineProps<{
    /** 骨架行数；表格/列表加载时按视口高度调大 */
    rows?: number
    text?: string
    minHeight?: string
  }>(),
  { rows: 4, text: '', minHeight: '' },
)
</script>

<template>
  <div
    class="loading-block"
    :style="{ minHeight }"
    role="status"
    aria-live="polite"
    aria-busy="true"
  >
    <el-skeleton :rows="rows" animated />
    <p v-if="text" class="loading-block__text">{{ text }}</p>
  </div>
</template>

<style scoped>
.loading-block {
  padding: 16px 18px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.loading-block__text {
  margin: 12px 0 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}
</style>
