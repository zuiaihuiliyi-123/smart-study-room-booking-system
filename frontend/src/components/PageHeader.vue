<script setup lang="ts">
defineProps<{
  title: string
  subtitle?: string
}>()
</script>

<template>
  <header class="page-header">
    <div class="page-header__text">
      <h2>{{ title }}</h2>
      <p v-if="subtitle">{{ subtitle }}</p>
    </div>
    <div class="page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<style scoped>
.page-header {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: flex-start;
  justify-content: space-between;
  padding-bottom: 14px;
  margin-bottom: 18px;
  border-bottom: 1px solid var(--ssr-line);
}

.page-header__text {
  min-width: 0;
}

h2 {
  margin: 0;
  color: var(--ssr-ink);
  font-size: 22px;
  font-weight: 600;
  line-height: 1.35;
  letter-spacing: 0.2px;
}

p {
  margin: 6px 0 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  line-height: 1.6;
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
</style>
