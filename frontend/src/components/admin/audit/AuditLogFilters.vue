<script setup lang="ts">
import FilterBar from '@/components/FilterBar.vue'
import { ACTION_OPTIONS, TARGET_OPTIONS } from '@/utils/auditMeta'
import { isAfterToday } from '@/utils/format'

const props = defineProps<{
  loading: boolean
  operatorOptions: { id: number; label: string }[]
}>()

const emit = defineEmits<{
  (e: 'search'): void
  (e: 'reset'): void
}>()

const actionType = defineModel<string>('actionType', { required: true })
const operatorId = defineModel<number | ''>('operatorId', { required: true })
const targetType = defineModel<string>('targetType', { required: true })
const dateRange = defineModel<string[]>('dateRange', { required: true })

function disabledDate(value: Date): boolean {
  return isAfterToday(value)
}
</script>

<template>
  <FilterBar :loading="props.loading" @search="emit('search')" @reset="emit('reset')">
    <label class="filter-field">
      <span class="filter-field__label">操作类型</span>
      <el-select v-model="actionType" class="w-180" clearable placeholder="全部类型">
        <el-option label="全部类型" value="" />
        <el-option
          v-for="item in ACTION_OPTIONS"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-select>
    </label>

    <label class="filter-field">
      <span class="filter-field__label">操作人</span>
      <el-select v-model="operatorId" class="w-200" clearable filterable placeholder="全部操作人">
        <el-option label="全部操作人" value="" />
        <el-option
          v-for="item in props.operatorOptions"
          :key="item.id"
          :label="item.label"
          :value="item.id"
        />
      </el-select>
    </label>

    <label class="filter-field">
      <span class="filter-field__label">目标类型</span>
      <el-select v-model="targetType" class="w-160" clearable placeholder="全部目标">
        <el-option label="全部目标" value="" />
        <el-option
          v-for="item in TARGET_OPTIONS"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
      </el-select>
    </label>

    <label class="filter-field">
      <span class="filter-field__label">操作时间</span>
      <el-date-picker
        v-model="dateRange"
        class="w-260"
        type="daterange"
        value-format="YYYY-MM-DD"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        :disabled-date="disabledDate"
      />
    </label>
  </FilterBar>
</template>

<style scoped>
.w-160 {
  width: 160px;
}

.w-180 {
  width: 180px;
}

.w-200 {
  width: 200px;
}

.w-260 {
  width: 260px;
}
</style>
