<script setup lang="ts">
/**
 * 预约管理（FR-030 全量查询 / FR-011 强制取消 / FR-023 手动违约登记）。
 *
 * 页面范式：FilterBar（日期区间 + 自习室 + 状态 + 学号）→ 操作区 → el-table → 分页；
 * 详情与两个写操作都在 `ReservationDetailDrawer` 内完成，不叠第二个弹窗。
 *
 * 互斥口径（AGENTS.md §4 / BR-015）：强制取消仅「待使用」且不计违约；手动违约登记仅「使用中」
 * 且累加次数。表格的两个操作按钮按状态互斥禁用，抽屉内也直接写明两者区别。
 */
import { onMounted } from 'vue'
import ReservationDetailDrawer from '@/components/admin/ReservationDetailDrawer.vue'
import EmptyState from '@/components/EmptyState.vue'
import FilterBar from '@/components/FilterBar.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import { seatIdLabel, userLabelOf } from '@/utils/adminData'
import { bracketRangeText } from '@/utils/bookingRules'
import { formatDateTime } from '@/utils/format'
import { useReservationManage } from '@/utils/useReservationManage'

const {
  scopeLabel,
  rooms,
  directory,
  items,
  total,
  loading,
  refreshing,
  errorMessage,
  dateRange,
  roomId,
  statusFilter,
  studentNo,
  page,
  pageSize,
  detailVisible,
  detail,
  detailLoading,
  detailError,
  canForceCancel,
  canRegisterViolation,
  detailUserViolations,
  load,
  refresh,
  onSearch,
  onReset,
  onPageChange,
  onPageSizeChange,
  openDetail,
  forceCancel,
  registerViolation,
  clockText,
  disabledDate,
} = useReservationManage()


onMounted(() => {
  void load()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="预约管理"
      subtitle="预约全量查询 · 强制取消（不计违约）· 手动违约登记（累加次数）· 同一预约单两个操作互斥"
    />

    <FilterBar :loading="loading" @search="onSearch" @reset="onReset">
      <label class="filter-field">
        <span class="filter-field__label">预约日期</span>
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
        <span class="filter-field__label">自习室</span>
        <el-select v-model="roomId" class="w-160" clearable placeholder="全部自习室">
          <el-option v-for="room in rooms" :key="room.id" :label="room.name" :value="room.id" />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">状态</span>
        <el-select v-model="statusFilter" class="w-130">
          <el-option label="全部" value="全部" />
          <el-option label="待使用" value="待使用" />
          <el-option label="使用中" value="使用中" />
          <el-option label="已完成" value="已完成" />
          <el-option label="已取消" value="已取消" />
          <el-option label="已违约" value="已违约" />
        </el-select>
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
      <span class="admin-toolbar__hint">操作范围：{{ scopeLabel }} · 共 {{ total }} 条预约</span>
    </div>

    <section class="ssr-card">
      <LoadingBlock v-if="loading" :rows="6" text="正在读取预约单…" />

      <div v-else-if="errorMessage" class="panel">
        <el-alert type="error" :closable="false" show-icon title="预约列表读取失败">
          <p>{{ errorMessage }}</p>
        </el-alert>
        <el-button type="primary" plain @click="load">重试</el-button>
      </div>

      <EmptyState
        v-else-if="items.length === 0"
        description="当前筛选条件下没有预约单。可放宽日期区间或清空状态 / 学号筛选"
      />

      <template v-else>
        <div class="table-wrap">
          <el-table :data="items" size="small" border style="min-width: 1120px">
            <el-table-column label="预约单号" width="96">
              <template #default="{ row }">
                <el-button link type="primary" @click="openDetail(row)">#{{ row.id }}</el-button>
              </template>
            </el-table-column>

            <el-table-column label="使用人" min-width="180">
              <template #default="{ row }">{{ userLabelOf(directory, row.user_id) }}</template>
            </el-table-column>

            <el-table-column label="座位" min-width="180">
              <template #default="{ row }">{{ seatIdLabel(directory, row.seat_id) }}</template>
            </el-table-column>

            <el-table-column label="预约日期" width="112" prop="reserve_date" />

            <el-table-column label="时段（左闭右开）" width="132">
              <template #default="{ row }">
                {{ bracketRangeText(row.start_time, row.end_time) }}
              </template>
            </el-table-column>

            <el-table-column label="状态" width="96">
              <template #default="{ row }">
                <StatusTag kind="reservation" :value="row.status" />
              </template>
            </el-table-column>

            <el-table-column label="签到 / 签退" width="124">
              <template #default="{ row }">
                <el-tooltip
                  placement="top"
                  :content="`签到：${formatDateTime(row.check_in_time)}　签退：${formatDateTime(row.check_out_time)}（完整时间见详情）`"
                >
                  <div>
                    <div>签到 {{ clockText(row.check_in_time) }}</div>
                    <div>签退 {{ clockText(row.check_out_time) }}</div>
                  </div>
                </el-tooltip>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="230" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>

                <el-tooltip
                  v-if="row.status !== '待使用'"
                  content="强制取消仅适用于「待使用」的预约"
                  placement="top"
                >
                  <span>
                    <el-button link type="danger" size="small" disabled>强制取消</el-button>
                  </span>
                </el-tooltip>
                <el-button v-else link type="danger" size="small" @click="openDetail(row)">
                  强制取消
                </el-button>

                <el-tooltip
                  v-if="row.status !== '使用中'"
                  content="手动违约登记仅适用于「使用中」的预约"
                  placement="top"
                >
                  <span>
                    <el-button link type="warning" size="small" disabled>违约登记</el-button>
                  </span>
                </el-tooltip>
                <el-button v-else link type="warning" size="small" @click="openDetail(row)">
                  违约登记
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

    <el-alert class="notice" type="info" :closable="false" show-icon title="「强制取消」与「手动违约登记」的区别">
      <p>
        <strong>强制取消</strong>只对「待使用」有效，用于事前终止；
          不产生违约记录、不累加违约次数，取消后该时段立即对其他同学开放。
          </p>
          <p>
            <strong>手动违约登记</strong>只对「使用中」有效，用于事后追责；
              必填原因并写入审计日志，会累加用户违约次数，累计 3 次触发 7 天限制。
              </p>
              <p>两者互斥：同一预约单不会同时出现两个可用按钮。</p>
              <p>列表中「签到 / 签退」只显示时刻（同一预约单只涉及一天），完整时间见详情抽屉。</p>
            </el-alert>

            <ReservationDetailDrawer
              v-model="detailVisible"
              :detail="detail"
              :loading="detailLoading"
              :loading-error="detailError"
              :directory="directory"
              :scope-label="scopeLabel"
              :can-force-cancel="canForceCancel"
              :can-register-violation="canRegisterViolation"
              :user-violation-count="detailUserViolations"
              @force-cancel="forceCancel"
              @register-violation="registerViolation"
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

.w-260 {
  width: 260px;
}
</style>






