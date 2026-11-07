<script setup lang="ts">
/**
 * 评价管理（FR-041 / BR-013）。
 *
 * 只读页面：评价由学生在「已完成」预约上提交，一单一评；
 * 管理端可按评分与提交日期筛选，用于服务质量反馈。
 * 不提供修改 / 删除评价，也不改变预约、违约或账户状态。
 */
import { onMounted } from 'vue'

import EmptyState from '@/components/EmptyState.vue'
import FilterBar from '@/components/FilterBar.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import PageHeader from '@/components/PageHeader.vue'
import { reservationLabelOf, userLabelOf } from '@/utils/adminData'
import { formatDateTime, isAfterToday } from '@/utils/format'
import { useReviewManage } from '@/utils/useReviewManage'

const {
  directory,
  items,
  total,
  loading,
  refreshing,
  errorMessage,
  scoreFilter,
  dateRange,
  page,
  pageSize,
  load,
  refresh,
  onSearch,
  onReset,
  onPageChange,
  onPageSizeChange,
} = useReviewManage()

function disabledDate(value: Date): boolean {
  // 评价只可能发生在过去，未来日期没有查询意义
  return isAfterToday(value)
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="评价管理"
      subtitle="查看学生对已完成预约的评价，用于服务质量反馈"
    />

    <FilterBar :loading="loading" @search="onSearch" @reset="onReset">
      <label class="filter-field">
        <span class="filter-field__label">评分</span>
        <el-select v-model="scoreFilter" class="w-140">
          <el-option label="全部评分" value="" />
          <el-option label="5 星" :value="5" />
          <el-option label="4 星" :value="4" />
          <el-option label="3 星" :value="3" />
          <el-option label="2 星" :value="2" />
          <el-option label="1 星" :value="1" />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">提交时间</span>
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

    <div class="admin-toolbar">
      <div class="admin-toolbar__buttons">
        <el-button :loading="refreshing" @click="refresh()">刷新</el-button>
      </div>
      <span class="admin-toolbar__hint">全站评价 · 共 {{ total }} 条</span>
    </div>

    <section class="ssr-card">
      <LoadingBlock v-if="loading" :rows="6" text="正在读取评价…" />

      <div v-else-if="errorMessage" class="panel">
        <el-alert type="error" :closable="false" show-icon title="评价列表读取失败">
          <p>{{ errorMessage }}</p>
        </el-alert>
        <el-button type="primary" plain @click="load">重试</el-button>
      </div>

      <EmptyState
        v-else-if="items.length === 0"
        description="当前筛选条件下没有评价。可放宽评分或提交时间筛选"
      />

      <template v-else>
        <div class="table-wrap">
          <el-table :data="items" size="small" border style="min-width: 1120px">
            <el-table-column label="评价号" width="92">
              <template #default="{ row }">
                <strong>#{{ row.id }}</strong>
              </template>
            </el-table-column>

            <el-table-column label="学生" min-width="180">
              <template #default="{ row }">
                {{ userLabelOf(directory, row.user_id) }}
              </template>
            </el-table-column>

            <el-table-column label="评分" width="180">
              <template #default="{ row }">
                <el-rate
                  :model-value="row.score"
                  disabled
                  show-score
                  score-template="{value} 分"
                />
              </template>
            </el-table-column>

            <el-table-column label="评价内容" min-width="280" show-overflow-tooltip>
              <template #default="{ row }">
                <span v-if="row.content">{{ row.content }}</span>
                <span v-else class="ssr-text-muted">未填写文字评价</span>
              </template>
            </el-table-column>

            <el-table-column label="关联预约" min-width="260">
              <template #default="{ row }">
                {{ reservationLabelOf(directory, row.reservation_id) }}
              </template>
            </el-table-column>

            <el-table-column label="提交时间" width="150">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>
          </el-table>
        </div>

        <div class="pager" role="navigation" aria-label="分页">
          <el-pagination
            background
            layout="total, sizes, prev, pager, next"
            :total="total"
            :current-page="page"
            :page-size="pageSize"
            :page-sizes="[20, 50, 100]"
            @current-change="onPageChange"
            @size-change="onPageSizeChange"
          />
        </div>
      </template>
    </section>

    <el-alert class="notice" type="info" :closable="false" show-icon title="关于评价">
      <p>
        评价来自学生对「已完成」预约的一单一评（BR-013）；本页只读，不提供修改或删除入口。
      </p>
      <p>评分与文字仅用于服务质量反馈，不改变预约、违约或账户状态。</p>
    </el-alert>
  </div>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
}

.panel p {
  margin: 0;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

.notice {
  margin-top: 12px;
}

.notice p {
  margin: 0 0 4px;
  font-size: var(--ssr-font-note);
  line-height: 1.6;
}

.notice p:last-child {
  margin-bottom: 0;
}

.w-140 {
  width: 140px;
}

.w-260 {
  width: 260px;
}
</style>
