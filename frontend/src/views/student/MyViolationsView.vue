<script setup lang="ts">
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="我的违约"
    description="查看本人违约记录、原因与账户受限状态（FR-032）。"
    :tasks="[
      '接入 GET /violations/me，展示违约类型、时间、原因与关联预约',
      '展示累计违约次数与距离账户受限的阈值提示',
      '说明自动违约与手动违约的判定口径',
    ]"
  />
</template>
