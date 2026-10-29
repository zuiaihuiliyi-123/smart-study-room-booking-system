<script setup lang="ts">
import { computed } from 'vue'
import type { EChartsOption } from 'echarts'

import BaseChart from '@/components/BaseChart.vue'
import PageHeader from '@/components/PageHeader.vue'

const stats = [
  { label: '座位总数', value: 0 },
  { label: '使用中预约', value: 0 },
  { label: '今日预约', value: 0 },
  { label: '今日违约', value: 0 },
  { label: '受限账户', value: 0 },
]

// TODO: 接入 GET /dashboard/overview，并按 FR-053 每 10 秒刷新
const seatUsageOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  grid: { left: 40, right: 20, top: 30, bottom: 40 },
  xAxis: { type: 'category', data: [] },
  yAxis: { type: 'value' },
  series: [{ name: '使用时段数', type: 'bar', data: [] }],
}))

// TODO: 接入 GET /dashboard/trend
const trendOption = computed<EChartsOption>(() => ({
  tooltip: { trigger: 'axis' },
  legend: { data: ['有效预约', '违约'] },
  grid: { left: 40, right: 20, top: 40, bottom: 40 },
  xAxis: { type: 'category', data: [] },
  yAxis: { type: 'value' },
  series: [
    { name: '有效预约', type: 'line', data: [] },
    { name: '违约', type: 'line', data: [] },
  ],
}))
</script>

<template>
  <div class="page">
    <PageHeader
      title="数据看板"
      subtitle="骨架页：接入 /api/v1/dashboard/* 后展示实时数据，并按 FR-053 每 10 秒刷新"
    />

    <div class="stats-grid">
      <el-card v-for="item in stats" :key="item.label" class="stat-card">
        <div class="stat-value">{{ item.value }}</div>
        <div class="stat-label">{{ item.label }}</div>
      </el-card>
    </div>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header>座位使用时段数（FR-050）</template>
          <BaseChart :option="seatUsageOption" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <template #header>预约与违约趋势（FR-051）</template>
          <BaseChart :option="trendOption" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.stat-card {
  text-align: center;
}
.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #409eff;
}
.stat-label {
  margin-top: 6px;
  color: #909399;
  font-size: 13px;
}
</style>
