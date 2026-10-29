<script setup lang="ts">
/**
 * 投诉处理（FR-043 + BR-014）。
 *
 * 默认进入「待处理」队列（管理员的实际工作入口），可按状态 / 对象类型 / 提交时间筛选；
 * 处理在 `ComplaintHandleDrawer` 内完成（状态流转 + 必填处理说明）。
 *
 * BR-014（3 个工作日）：超时行整行标红并直接显示「已超时 N 天」，同时给出精确截止时刻。
 * 需注意需求原文：超时只以**站内提示**提醒受理人、**不设自动升级**（UC-10 异常流程）；
 * 本页的标红与天数只是界面层辅助，不构成新的业务规则。
 */
import { onMounted } from 'vue'

import ComplaintHandleDrawer from '@/components/admin/ComplaintHandleDrawer.vue'
import EmptyState from '@/components/EmptyState.vue'
import FilterBar from '@/components/FilterBar.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import type { Complaint } from '@/types'
import { formatDateTime, isAfterToday } from '@/utils/format'
import { useComplaintManage } from '@/utils/useComplaintManage'

const {
  scopeLabel,
  directory,
  items,
  total,
  loading,
  refreshing,
  errorMessage,
  statusFilter,
  targetFilter,
  dateRange,
  page,
  pageSize,
  detailVisible,
  detail,
  submitting,
  overdueCount,
  slaWorkdays,
  load,
  refresh,
  onSearch,
  onReset,
  onPageChange,
  onPageSizeChange,
  openDetail,
  submitHandle,
  nextActions,
  targetText,
  slaOf,
} = useComplaintManage()

function disabledDate(value: Date): boolean {
  return isAfterToday(value)
}

function rowClass({ row }: { row: Complaint }): string {
  // 只有尚未给出处理结果的投诉才谈得上「超时」（BR-014 要求 3 个工作日内给出处理结果）
  const pending = row.status === '待处理' || row.status === '处理中'
  return pending && slaOf(row).overdue ? 'ssr-row-overdue' : ''
}

async function onHandle(
  status: '待处理' | '处理中' | '已处理' | '已驳回' | '已关闭',
  note: string,
): Promise<void> {
  await submitHandle(status, note)
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="投诉处理"
      subtitle="投诉受理 / 处理 / 驳回 · 处理时限 3 个工作日（超时仅站内提示，不设自动升级）· 状态流转严格按「待处理 → 处理中 → 已处理 / 已驳回」"
    />

    <FilterBar :loading="loading" @search="onSearch" @reset="onReset">
      <label class="filter-field">
        <span class="filter-field__label">状态</span>
        <el-select v-model="statusFilter" class="w-200">
          <el-option label="待处理（默认队列）" value="待处理" />
          <el-option label="处理中" value="处理中" />
          <el-option label="已处理" value="已处理" />
          <el-option label="已驳回" value="已驳回" />
          <el-option label="已关闭" value="已关闭" />
          <el-option label="全部" value="全部" />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">投诉对象</span>
        <el-select v-model="targetFilter" class="w-140">
          <el-option label="全部" value="全部" />
          <el-option label="座位" value="座位" />
          <el-option label="自习室" value="自习室" />
          <el-option label="预约单" value="预约单" />
          <el-option label="用户" value="用户" />
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
      <span class="admin-toolbar__hint">
        操作范围：{{ scopeLabel }} · 共 {{ total }} 条 · 本页超时 {{ overdueCount }} 条（时限 {{ slaWorkdays }} 个工作日）
      </span>
    </div>

    <section class="ssr-card">
      <LoadingBlock v-if="loading" :rows="6" text="正在读取投诉队列…" />

      <div v-else-if="errorMessage" class="panel">
        <el-alert type="error" :closable="false" show-icon title="投诉队列读取失败">
          <p>{{ errorMessage }}</p>
        </el-alert>
        <el-button type="primary" plain @click="load">重试</el-button>
      </div>

      <EmptyState
        v-else-if="items.length === 0"
        description="当前筛选条件下没有投诉。默认队列为「待处理」，可切换状态或放宽提交时间后再查"
      />

      <template v-else>
        <div class="table-wrap">
          <el-table :data="items" size="small" border :row-class-name="rowClass" style="min-width: 1000px">
            <el-table-column label="投诉号" width="84">
              <template #default="{ row }">
                <el-button link type="primary" @click="openDetail(row)">#{{ row.id }}</el-button>
              </template>
            </el-table-column>

            <el-table-column label="投诉对象" min-width="170">
              <template #default="{ row }">{{ targetText(row) }}</template>
            </el-table-column>

            <el-table-column label="投诉内容" min-width="240" show-overflow-tooltip>
              <template #default="{ row }">{{ row.content }}</template>
            </el-table-column>

            <el-table-column label="状态" width="88">
              <template #default="{ row }">
                <StatusTag kind="complaint" :value="row.status" />
              </template>
            </el-table-column>

            <el-table-column label="提交时间" width="140">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>

            <el-table-column label="处理时限" min-width="210">
              <template #default="{ row }">
                <span>{{ slaOf(row).deadlineText }}</span>
                <div v-if="slaOf(row).overdue" class="overdue-text">
                  已超时 {{ slaOf(row).overdueDays }} 天
                </div>
                <div v-else-if="row.status === '待处理' || row.status === '处理中'" class="ssr-text-muted">
                  尚余 {{ slaOf(row).remainingWorkdays }} 个工作日
                </div>
              </template>
            </el-table-column>


            <el-table-column label="操作" width="96" fixed="right">
              <template #default="{ row }">
                <el-button
                  link
                  :type="nextActions(row).length > 0 ? 'primary' : 'info'"
                  size="small"
                  @click="openDetail(row)"
                >
                  {{ nextActions(row).length > 0 ? '处理' : '查看' }}
                </el-button>
              </template>
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

    <el-alert class="notice" type="info" :closable="false" show-icon title="超时口径与处理时限">
      <p>
        投诉自提交起 <strong>{{ slaWorkdays }} 个工作日</strong>内应给出处理结果；
        本版按「跳过周六 / 周日」计算（法定节假日无数据源，不计算），表中同时给出精确截止时刻。
      </p>
      <p>
        需求原文说明：超时通过<strong>站内提示</strong>提醒受理人，<strong>不设自动升级</strong>（异常流程），
        因此本页只做标红与天数提示，不会自动关闭或升级投诉。
      </p>
    </el-alert>

    <ComplaintHandleDrawer
      v-model="detailVisible"
      :complaint="detail"
      :directory="directory"
      :scope-label="scopeLabel"
      :submitting="submitting"
      :actions="nextActions(detail)"
      @handle="onHandle"
    />
  </div>
</template>

<style scoped>
.notice {
  margin-top: 12px;
}

.notice p {
  margin: 0 0 4px;
  font-size: var(--ssr-font-note);
  line-height: 1.6;
}

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

.overdue-text {
  color: var(--ssr-danger);
  font-weight: 600;
}

.w-260 {
  width: 260px;
}
</style>







