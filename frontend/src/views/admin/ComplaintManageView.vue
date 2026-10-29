<script setup lang="ts">
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="投诉处理"
    description="受理、处理或驳回学生投诉，并向学生反馈（FR-043）。"
    :tasks="[
      '接入 GET /complaints 与 PATCH /complaints/{id}',
      '展示投诉对象、内容、状态与提交时间',
      '处理时填写处理说明，记录处理人与时间',
      '超过处理时限的投诉自动关闭（ST-063）',
    ]"
  />
</template>
