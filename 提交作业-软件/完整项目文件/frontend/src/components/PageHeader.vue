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
  align-items: center;
  justify-content: space-between;
  padding-bottom: 10px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--ssr-line);
}

.page-header__text {
  min-width: 0;
}

h2 {
  margin: 0;
  color: var(--ssr-ink);
  font-size: 20px;
  font-weight: 600;
  line-height: 1.3;
  letter-spacing: 0.2px;
}

p {
  margin: 3px 0 0;
  color: var(--ssr-muted-ink);
  font-size: calc(var(--ssr-font-note) - 1px);
  line-height: 1.5;
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}
</style>
