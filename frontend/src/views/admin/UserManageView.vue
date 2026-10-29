<script setup lang="ts">
import ModulePlaceholder from '@/components/ModulePlaceholder.vue'
</script>

<template>
  <ModulePlaceholder
    title="用户管理"
    description="查询用户与账户状态，处理黑名单相关操作（FR-040 / FR-044）。"
    :tasks="[
      '接入 GET /users 展示姓名、学号/工号、角色、账户状态、违约次数',
      '管理员不得修改用户身份信息与口令',
      '账户状态变更通过黑名单流程执行并留下记录',
      '学生个人敏感信息按最小化原则展示（LC-01）',
    ]"
  />
</template>
