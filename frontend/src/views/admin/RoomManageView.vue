<script setup lang="ts">
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="自习室管理"
    description="维护自习室与区域，采用停用而非物理删除（FR-001 / FR-002）。"
    :tasks="[
      '接入 GET/POST /rooms 与区域接口',
      '表格展示名称、位置、开放时间、容量、启用状态',
      '停用自习室前提示影响的座位与未来预约',
      '所有关键操作写入审计日志（NFR-009）',
    ]"
  />
</template>
