<script setup lang="ts">
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="预约管理"
    description="查询全部预约，执行强制取消与手动违约登记（FR-031 / FR-011 / FR-023）。"
    :tasks="[
      '接入 GET /reservations，按用户、座位、日期、状态筛选',
      '强制取消仅针对“待使用”，必须填写原因并审计',
      '强制取消与手动违约互斥，避免重复处置',
      '展示预约占用区间 [s, e) 与前后相邻预约',
    ]"
  />
</template>
