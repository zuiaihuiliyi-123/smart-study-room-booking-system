<script setup lang="ts">
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="预约座位"
    description="选择自习室、日期与时段，查询可预约座位并创建预约（FR-013 / FR-010）。"
    :tasks="[
      '接入 GET /reservations/available-seats，展示座位图与筛选条件',
      '按 C1～C6 展示不可预约原因与具体参数',
      '创建预约时生成幂等键，处理并发冲突提示',
      '预约成功后展示站内通知与下一步签到提示',
    ]"
  />
</template>
