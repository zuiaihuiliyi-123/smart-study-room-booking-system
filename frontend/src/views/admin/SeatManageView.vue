<script setup lang="ts">
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="座位管理"
    description="维护座位信息、查看资源状态与预约占用（FR-002 / FR-003 / FR-004）。"
    :tasks="[
      '接入 GET /rooms/{room_id}/seats 与 POST /seats',
      '以座位图展示“可用 / 维修中 / 停用”，不展示“已预约”资源状态',
      '调整状态前列出冲突的未来预约，不自动取消（BR-019）',
      '状态调整写入审计日志并记录原因',
    ]"
  />
</template>
