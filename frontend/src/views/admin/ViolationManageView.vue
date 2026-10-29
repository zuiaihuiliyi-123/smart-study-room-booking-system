<script setup lang="ts">
/**
 * 违约记录管理（FR-032）。
 *
 * 查询口径：违约类型 + 产生时间区间 + 学号（全部服务端分页）→ 列表 → 详情抽屉。
 * 只读页面：不含导出（FR-033 已排除），也不设「撤销违约 / 申诉」入口（FR-024 已排除）。
 * 手动违约登记的**入口在「预约管理」页的详情抽屉**（FR-023 只能针对「使用中」的预约单），
 * 本页因此不重复提供写操作，避免出现两个来源不一致的登记入口。
 */
import { onMounted } from 'vue'

import ViolationDetailDrawer from '@/components/admin/ViolationDetailDrawer.vue'
import EmptyState from '@/components/EmptyState.vue'
import FilterBar from '@/components/FilterBar.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import { operatorLabelOf, reservationLabelOf, userLabelOf } from '@/utils/adminData'
import { formatDateTime, isAfterToday } from '@/utils/format'
import { useViolationManage } from '@/utils/useViolationManage'

const {
  scopeLabel,
  directory,
  items,
  total,
  loading,
  refreshing,
  errorMessage,
  typeFilter,
  dateRange,
  studentNo,
  page,
  pageSize,
  detailVisible,
  detail,
  load,
  refresh,
  onSearch,
  onReset,
  onPageChange,
  onPageSizeChange,
  openDetail,
} = useViolationManage()

function disabledDate(value: Date): boolean {
  return isAfterToday(value)
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="违约记录管理"
      subtitle="违约记录查询 · 只读：不含导出与申诉（两项均已裁定排除）；手动违约登记入口在「预约管理」页"
    />

    <FilterBar :loading="loading" @search="onSearch" @reset="onReset">
      <label class="filter-field">
        <span class="filter-field__label">违约类型</span>
        <el-select v-model="typeFilter" class="w-140">
          <el-option label="全部" value="全部" />
          <el-option label="自动违约" value="自动违约" />
          <el-option label="手动违约" value="手动违约" />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">产生时间</span>
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

      <label class="filter-field">
        <span class="filter-field__label">学号</span>
        <el-input
          v-model="studentNo"
          class="w-160"
          clearable
          placeholder="精确匹配学号"
          @keyup.enter="onSearch"
        />
      </label>
    </FilterBar>

    <div class="admin-toolbar">
      <div class="admin-toolbar__buttons">
        <el-button :loading="refreshing" @click="refresh()">刷新</el-button>
      </div>
      <span class="admin-toolbar__hint">操作范围：{{ scopeLabel }} · 共 {{ total }} 条违约记录</span>
    </div>

    <section class="ssr-card">
      <LoadingBlock v-if="loading" :rows="6" text="正在读取违约记录…" />

      <div v-else-if="errorMessage" class="panel">
        <el-alert type="error" :closable="false" show-icon title="违约记录读取失败">
          <p>{{ errorMessage }}</p>
        </el-alert>
        <el-button type="primary" plain @click="load">重试</el-button>
      </div>

      <EmptyState
        v-else-if="items.length === 0"
        description="当前筛选条件下没有违约记录。可放宽时间区间或清空类型 / 学号筛选"
      />

      <template v-else>
        <div class="table-wrap">
          <el-table :data="items" size="small" border style="min-width: 1080px">
            <el-table-column label="记录号" width="92">
              <template #default="{ row }">
                <el-button link type="primary" @click="openDetail(row)">#{{ row.id }}</el-button>
              </template>
            </el-table-column>

            <el-table-column label="用户" min-width="180">
              <template #default="{ row }">{{ userLabelOf(directory, row.user_id) }}</template>
            </el-table-column>

            <el-table-column label="违约类型" width="110">
              <template #default="{ row }">
                <StatusTag kind="violation" :value="row.type" />
              </template>
            </el-table-column>

            <el-table-column label="违约原因" min-width="220">
              <template #default="{ row }">{{ row.reason }}</template>
            </el-table-column>

            <el-table-column label="关联预约单" min-width="240">
              <template #default="{ row }">
                {{ reservationLabelOf(directory, row.reservation_id) }}
              </template>
            </el-table-column>

            <el-table-column label="登记人" min-width="150">
              <template #default="{ row }">
                {{ operatorLabelOf(directory, row.operator_id) }}
              </template>
            </el-table-column>

            <el-table-column label="记录时间" width="150">
              <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
            </el-table-column>

            <el-table-column label="操作" width="90" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
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

    <el-alert class="notice" type="info" :closable="false" show-icon title="口径说明">
      <p>
        有效违约记录 = 「自动违约」（签到截止后系统判定）与「手动违约」（管理员登记）
        两类；累计达到 3 次由系统限制账户 7 天。
      </p>
      <p>
        本页不含导出（已裁定排除）。审计留痕由后端记录，本版同样不提供审计日志导出。
      </p>
    </el-alert>

    <ViolationDetailDrawer v-model="detailVisible" :violation="detail" :directory="directory" />
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

.w-260 {
  width: 260px;
}
</style>




