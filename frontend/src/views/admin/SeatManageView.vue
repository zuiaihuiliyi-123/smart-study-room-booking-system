<script setup lang="ts">
/**
 * 座位管理（FR-003 资源状态查询 / FR-004 资源状态维护 / FR-031 实时占用展示）。
 *
 * 页面范式：FilterBar（自习室 + 分区 + 资源状态 + 时段占用 + 日期时段）→ 操作区（视图切换、
 * 选择与批量调整）→ 网格视图 / 列表视图 → 分页。资源状态调整走 `SeatStatusDrawer`（抽屉，
 * 内含 BR-019 冲突清单与二次确认），不在表格或格子上直接改状态，避免误操作。
 *
 * 口径提醒（需求原文）：FR-003 要求同时呈现**资源状态**与**该时段占用**，两者在不同列 / 不同
 * 标记上分开呈现，不合并成一个「状态」；「已被预约」不改变任何座位状态（AGENTS.md §4）。
 */
import { onMounted } from 'vue'

import SeatGridPanel from '@/components/admin/SeatGridPanel.vue'
import SeatListTable from '@/components/admin/SeatListTable.vue'
import SeatStatusDrawer from '@/components/admin/SeatStatusDrawer.vue'
import EmptyState from '@/components/EmptyState.vue'
import FilterBar from '@/components/FilterBar.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import PageHeader from '@/components/PageHeader.vue'
import type { SeatOccupancy } from '@/types'
import { isBeforeToday } from '@/utils/format'
import { useSeatManage } from '@/utils/useSeatManage'

const {
  scopeLabel,
  rooms,
  roomId,
  areaId,
  statusFilter,
  occupancyFilter,
  view,
  reserveDate,
  startTime,
  endTime,
  directory,
  items,
  loading,
  refreshing,
  errorMessage,
  occupancyNote,
  page,
  pageSize,
  total,
  paged,
  selectedIds,
  selectedSeats,
  availableIds,
  areaOptions,
  gridGroups,
  timeError,
  statusDrawerVisible,
  targetStatus,
  reason,
  conflictFrom,
  conflictTo,
  conflicts,
  conflictsQueried,
  conflictLoading,
  conflictError,
  executing,
  load,
  refresh,
  onSearch,
  onReset,
  onRoomChange,
  onPageChange,
  toggleSeat,
  selectGroup,
  clearSelection,
  openStatusDrawer,
  checkConflicts,
  executeStatusChange,
} = useSeatManage()

/** 只允许查询今天及以后：占用口径与可预约范围（BR-002 提前 7 天）保持一致 */
function disabledDate(value: Date): boolean {
  return isBeforeToday(value)
}

function onPageSizeChange(next: number): void {
  pageSize.value = next
  page.value = 1
}

function onSelectionChange(ids: number[]): void {
  selectedIds.value = ids
}

function onOpenSeat(row: SeatOccupancy): void {
  openStatusDrawer(row.seat)
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="座位管理"
      subtitle="资源状态查询 · 座位信息维护 · 当前时段占用展示 · 批量调整须先列冲突清单并二次确认"
    />

    <FilterBar :loading="loading" @search="onSearch" @reset="onReset">
      <label class="filter-field">
        <span class="filter-field__label">自习室</span>
        <el-select v-model="roomId" class="w-160" placeholder="请选择自习室" @change="onRoomChange">
          <el-option v-for="room in rooms" :key="room.id" :label="room.name" :value="room.id" />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">分区</span>
        <el-select v-model="areaId" class="w-150">
          <el-option label="全部分区" value="all" />
          <el-option v-for="area in areaOptions" :key="area.id" :label="area.name" :value="area.id" />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">资源状态</span>
        <el-select v-model="statusFilter" class="w-120">
          <el-option label="全部" value="全部" />
          <el-option label="可用" value="可用" />
          <el-option label="维修中" value="维修中" />
          <el-option label="停用" value="停用" />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">时段占用</span>
        <el-select v-model="occupancyFilter" class="w-130">
          <el-option label="全部" value="全部" />
          <el-option label="可约" value="可约" />
          <el-option label="已被预约" value="已被预约" />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">占用判定日期</span>
        <el-date-picker
          v-model="reserveDate"
          class="w-150"
          type="date"
          value-format="YYYY-MM-DD"
          :disabled-date="disabledDate"
          placeholder="选择日期"
        />
      </label>

      <label class="filter-field">
        <span class="filter-field__label">时段</span>
        <el-time-select v-model="startTime" class="w-120" start="06:00" step="00:30" end="23:30" placeholder="开始" />
        <span class="ssr-text-muted">至</span>
        <el-time-select v-model="endTime" class="w-120" start="06:30" step="00:30" end="23:30" placeholder="结束" />
      </label>
    </FilterBar>

    <div class="admin-toolbar">
      <div class="admin-toolbar__buttons">
        <el-radio-group v-model="view">
          <el-radio-button value="grid">网格视图</el-radio-button>
          <el-radio-button value="list">列表视图</el-radio-button>
        </el-radio-group>
        <el-button type="primary" :disabled="selectedIds.length === 0" @click="openStatusDrawer()">
          调整资源状态（已选 {{ selectedIds.length }}）
        </el-button>
        <el-button :disabled="selectedIds.length === 0" @click="clearSelection">清空选择</el-button>
        <el-button :loading="refreshing" @click="refresh()">刷新</el-button>
      </div>
      <span class="admin-toolbar__hint">操作范围：{{ scopeLabel }}</span>
    </div>

    <el-alert v-if="timeError !== ''" class="notice" type="warning" :closable="false" show-icon :title="timeError">
      <p v-if="occupancyNote !== ''">{{ occupancyNote }}</p>
    </el-alert>

    <section class="ssr-card">
      <LoadingBlock v-if="loading" :rows="5" text="正在读取座位与占用…" />

      <div v-else-if="errorMessage" class="panel">
        <el-alert type="error" :closable="false" show-icon title="座位数据读取失败">
          <p>{{ errorMessage }}</p>
        </el-alert>
        <el-button type="primary" plain @click="load">重试</el-button>
      </div>

      <EmptyState
        v-else-if="total === 0"
        description="当前筛选条件下没有座位。可切换自习室 / 分区，或清空「资源状态」「时段占用」筛选"
      />

      <template v-else>
        <SeatGridPanel
          v-if="view === 'grid'"
          :groups="gridGroups"
          :selected-ids="selectedIds"
          @toggle="toggleSeat"
          @select-group="selectGroup"
        />

        <template v-else>
          <SeatListTable
            :items="paged"
            :all-seats="items"
            :directory="directory"
            :selected-ids="selectedIds"
            @update:selected-ids="onSelectionChange"
            @open="onOpenSeat"
          />

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
      </template>
    </section>

    <el-alert class="notice" type="info" :closable="false" show-icon title="关于「资源状态」与「该时段占用」">
      <p>
        资源状态（可用 / 维修中 / 停用）是座位自身的属性，由本页的批量调整写入；
        该时段占用由选定日期与时段的实时查询得出，只用于查看与筛选。
        已被预约<strong>不会</strong>改动座位状态；调整座位状态也<strong>不会</strong>自动取消任何预约。
      </p>
      <p>
        已选 {{ selectedSeats.length }} 个座位；批量调整会先让你查询冲突清单，再二次确认。
        当前时段可约座位 {{ availableIds.size }} 个。
      </p>
    </el-alert>

    <SeatStatusDrawer
      v-model="statusDrawerVisible"
      v-model:target-status="targetStatus"
      v-model:reason="reason"
      v-model:conflict-from="conflictFrom"
      v-model:conflict-to="conflictTo"
      :scope-label="scopeLabel"
      :directory="directory"
      :seats="selectedSeats"
      :conflicts="conflicts"
      :conflicts-queried="conflictsQueried"
      :conflict-loading="conflictLoading"
      :conflict-error="conflictError"
      :executing="executing"
      @check="checkConflicts"
      @execute="executeStatusChange"
    />
  </div>
</template>

<style scoped>
.notice {
  margin-bottom: 12px;
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

.w-160 {
  width: 160px;
}
</style>




