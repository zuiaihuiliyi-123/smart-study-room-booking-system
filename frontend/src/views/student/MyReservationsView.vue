<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import PageHeader from '@/components/PageHeader.vue'
import ReservationTable from '@/components/reservations/ReservationTable.vue'
import ReviewDialog from '@/components/reservations/ReviewDialog.vue'
import type { Reservation } from '@/types'
import { useMyReservations } from '@/utils/useMyReservations'

const router = useRouter()
const {
  status,
  page: currentPage,
  pageSize,
  items,
  total,
  counts,
  loading,
  errorMessage,
  actingId,
  reviewedIds,
  directory,
  focusId,
  currentTab,
  tabs,
  gating,
  reviewTarget,
  reviewSubmitting,
  dateRange,
  roomId,
  rooms,
  onApplyFilters,
  onResetFilters,
  bootstrap,
  refresh,
  load,
  onTabChange,
  onPageChange,
  onPageSizeChange,
  onCheckIn,
  onCheckOut,
  onCancel,
  openReview,
  closeReview,
  submitReview,
} = useMyReservations()

function onReviewSubmit(payload: { score: number; content: string }): void {
  void submitReview(payload)
}

function onReview(item: Reservation): void {
  openReview(item)
}

onMounted(() => {
  void bootstrap()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="我的预约"
      subtitle="查看预约记录，取消预约、签到签退与评价"
    >
      <template #actions>
        <el-button :loading="loading" @click="refresh()">刷新</el-button>
        <el-button type="primary" @click="router.push('/student/booking')">预约座位</el-button>
      </template>
    </PageHeader>

    <div class="filters" role="search" aria-label="预约记录筛选">
      <el-date-picker
        v-model="dateRange"
        class="filters__date"
        type="daterange"
        value-format="YYYY-MM-DD"
        range-separator="至"
        start-placeholder="开始日期"
        end-placeholder="结束日期"
        @change="onApplyFilters"
      />
      <el-select
        v-model="roomId"
        class="filters__room"
        clearable
        placeholder="全部自习室"
        @change="onApplyFilters"
      >
        <el-option v-for="room in rooms" :key="room.id" :label="room.name" :value="room.id" />
      </el-select>
      <el-button @click="onResetFilters">重置筛选</el-button>
      <span class="ssr-text-muted filters__hint">按预约日期与自习室筛选，服务端过滤</span>
    </div>

    <el-tabs v-model="status" class="status-tabs" @tab-change="onTabChange">
      <el-tab-pane v-for="tab in tabs" :key="tab.value" :name="tab.value">
        <template #label>
          <span class="tab-label">
            {{ tab.label }}
            <em v-if="counts[tab.value] !== undefined" class="tab-label__count">
              {{ counts[tab.value] }}
            </em>
          </span>
        </template>
      </el-tab-pane>
    </el-tabs>

    <ReservationTable
      :items="items"
      :loading="loading"
      :error-message="errorMessage"
      :empty-text="currentTab.empty"
      :directory="directory"
      :reviewed-ids="reviewedIds"
      :acting-id="actingId"
      :focus-id="focusId"
      :gating="gating"
      @checkin="onCheckIn"
      @checkout="onCheckOut"
      @cancel="onCancel"
      @review="onReview"
      @retry="load"
    />

    <div v-if="!loading && !errorMessage && total > 0" class="pager">
      <el-pagination
        background
        layout="total, sizes, prev, pager, next, jumper"
        :total="total"
        :current-page="currentPage"
        :page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        @current-change="onPageChange"
        @size-change="onPageSizeChange"
      />
      <p class="ssr-text-muted pager__note">共 {{ total }} 条</p>
    </div>

    <p class="ssr-text-muted rules-note">
          取消规则：距开始<b>不少于 30 分钟</b>可无损取消；不足 30 分钟时用户不能自行取消，
          且该情形不计违约，只能由管理员强制取消。签到窗口为开始前 15 分钟至开始后 15 分钟。
        </p>

        <ReviewDialog
          :reservation="reviewTarget"
          :directory="directory"
          :submitting="reviewSubmitting"
          @submit="onReviewSubmit"
          @close="closeReview"
        />
      </div>
</template>

<style scoped>
.filters {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
}

.filters__date {
  max-width: 300px;
}

.filters__room {
  width: 170px;
}

.filters__hint {
  font-size: var(--ssr-font-note);
}

.status-tabs {
  margin-bottom: 4px;
}

.tab-label {
  display: inline-flex;
  gap: 5px;
  align-items: center;
  font-size: var(--ssr-font-body);
}

.tab-label__count {
  padding: 0 6px;
  color: var(--ssr-muted-ink);
  font-size: 11.5px;
  font-style: normal;
  background: var(--ssr-bg);
  border: 1px solid var(--ssr-line);
  border-radius: 9px;
}

.pager {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
  align-items: center;
  justify-content: space-between;
  padding: 12px 2px 0;
}

.pager__note {
  flex: 1 1 320px;
  margin: 0;
}

.rules-note {
  padding: 10px 12px;
  margin: 14px 0 0;
  background: var(--ssr-primary-light);
  border-radius: var(--ssr-radius-sm);
}
</style>
