<script setup lang="ts">
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="我的预约"
    description="查看本人预约记录，完成签到、签退与取消（FR-030 / FR-020 / FR-021 / FR-011）。"
    :tasks="[
      '接入 GET /reservations/me，按日期、状态、自习室筛选',
      '展示预约状态标签与签到窗口提示',
      '接入签到、签退、取消接口，操作后刷新列表',
      '演示数据包含待使用、使用中、已完成、已取消、已违约五种状态',
    ]"
  />
</template>
