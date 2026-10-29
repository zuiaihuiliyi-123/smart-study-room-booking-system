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
  margin-bottom: 14px;
}

.page-header__text {
  min-width: 0;
}

h2 {
  margin: 0;
  color: var(--ssr-ink);
  font-size: 18px;
  font-weight: 600;
  line-height: 1.4;
}

p {
  margin: 4px 0 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
</style>
