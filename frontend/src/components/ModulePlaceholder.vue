<script setup lang="ts">
import PageHeader from './PageHeader.vue'

defineProps<{
  title: string
  description?: string
  tasks?: string[]
}>()
</script>

<template>
  <div class="page">
    <PageHeader :title="title" :subtitle="description" />

    <el-card class="page-card">
      <el-empty description="页面骨架已就位，业务交互待实现">
        <ul v-if="tasks?.length" class="task-list">
          <li v-for="task in tasks" :key="task">{{ task }}</li>
        </ul>
      </el-empty>
    </el-card>
  </div>
</template>

<style scoped>
.task-list {
  margin: 0;
  padding: 0;
  list-style: none;
  color: #606266;
  font-size: 13px;
  line-height: 1.9;
  text-align: left;
}
</style>
