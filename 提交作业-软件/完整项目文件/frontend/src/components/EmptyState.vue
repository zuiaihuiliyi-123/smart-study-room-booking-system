<script setup lang="ts">
withDefaults(
  defineProps<{
    description?: string
    actionText?: string
    imageSize?: number
  }>(),
  { description: '暂无数据', actionText: '', imageSize: 80 },
)

const emit = defineEmits<{ (e: 'action'): void }>()
</script>

<template>
  <div class="empty-state">
    <el-empty :description="description" :image-size="imageSize">
      <slot name="action">
        <el-button v-if="actionText" type="primary" plain @click="emit('action')">
          {{ actionText }}
        </el-button>
      </slot>
    </el-empty>
  </div>
</template>

<style scoped>
.empty-state {
  padding: 8px 0;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}
</style>
