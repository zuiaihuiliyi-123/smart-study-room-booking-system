<script setup lang="ts">
import FilterBar from '@/components/FilterBar.vue'
import type { UserRoleFilter, UserStatusFilter } from '@/utils/useUserManage'

const props = defineProps<{ loading: boolean }>()

const emit = defineEmits<{
  (e: 'search'): void
  (e: 'reset'): void
}>()

const keyword = defineModel<string>('keyword', { required: true })
const roleFilter = defineModel<UserRoleFilter>('roleFilter', { required: true })
const statusFilter = defineModel<UserStatusFilter>('statusFilter', { required: true })
const violationMin = defineModel<number | null>('violationMin', { required: true })
</script>

<template>
  <FilterBar :loading="props.loading" @search="emit('search')" @reset="emit('reset')">
    <label class="filter-field">
      <span class="filter-field__label">姓名 / 学号</span>
      <el-input
        v-model="keyword"
        class="w-190"
        clearable
        placeholder="如：李明 / 3200104523"
        @keyup.enter="emit('search')"
      />
    </label>

    <label class="filter-field">
      <span class="filter-field__label">角色</span>
      <el-select v-model="roleFilter" class="w-150">
        <el-option label="全部" value="全部" />
        <el-option label="学生用户" value="学生用户" />
        <el-option label="自习室管理员" value="自习室管理员" />
        <el-option label="系统管理员" value="系统管理员" />
      </el-select>
    </label>

    <label class="filter-field">
      <span class="filter-field__label">账户状态</span>
      <el-select v-model="statusFilter" class="w-130">
        <el-option label="全部" value="全部" />
        <el-option label="正常" value="正常" />
        <el-option label="受限" value="受限" />
        <el-option label="停用" value="停用" />
      </el-select>
    </label>

    <label class="filter-field">
      <span class="filter-field__label">累计违约 ≥</span>
      <el-input-number v-model="violationMin" class="w-130" :min="0" :max="99" :step="1" />
    </label>
  </FilterBar>
</template>

<style scoped>
.w-130 {
  width: 130px;
}

.w-150 {
  width: 150px;
}

.w-190 {
  width: 190px;
}
</style>
