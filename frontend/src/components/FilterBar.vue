<script setup lang="ts">
withDefaults(
  defineProps<{
    loading?: boolean
    /** 是否显示"重置"；纯展示型过滤区可关掉 */
    showReset?: boolean
    searchText?: string
    resetText?: string
  }>(),
  {
    loading: false,
    showReset: true,
    searchText: '查询',
    resetText: '重置',
  },
)

const emit = defineEmits<{
  (e: 'search'): void
  (e: 'reset'): void
}>()
</script>

<template>
  <section class="filter-bar" role="search">
    <div class="filter-bar__fields">
      <slot />
    </div>
    <div class="filter-bar__actions">
      <el-button type="primary" :loading="loading" @click="emit('search')">
        {{ searchText }}
      </el-button>
      <el-button v-if="showReset" @click="emit('reset')">{{ resetText }}</el-button>
      <slot name="actions" />
    </div>
  </section>
</template>
