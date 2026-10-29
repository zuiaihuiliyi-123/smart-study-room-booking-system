<script setup lang="ts">
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="违约管理"
    description="查看违约记录并对“使用中”预约登记手动违约（FR-023 / FR-032）。"
    :tasks="[
      '接入 GET /violations 与 POST /violations/manual',
      '手动违约必须填写原因，记录操作人',
      '登记后累加违约次数，达到阈值触发账户受限（BR-009）',
      '自动违约记录只读，不允许管理员修改或删除',
    ]"
  />
</template>
