<script setup lang="ts">
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="我的投诉"
    description="提交投诉并查看处理进度与管理员反馈（FR-042 / FR-043）。"
    :tasks="[
      '接入 POST /complaints 提交投诉，校验投诉对象与内容',
      '接入 GET /complaints/me 展示状态时间线',
      '展示“待处理 / 处理中 / 已处理 / 已驳回 / 已关闭”状态',
    ]"
  />
</template>
