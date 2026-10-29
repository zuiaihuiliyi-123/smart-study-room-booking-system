<script setup lang="ts">
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="黑名单管理"
    description="查看、添加与解除黑名单，自动限制到期由定时任务处理（FR-044）。"
    :tasks="[
      '接入 GET/POST /blacklist 与解除接口',
      '手动加入必须填写原因与限制期限',
      '自动限制 7 天后解除；手动限制到期不得自动解除（BR-010）',
      '展示同一用户的历史记录与当前有效记录',
    ]"
  />
</template>
