<script setup lang="ts">
/**
 * 自习室管理（FR-001 / FR-002 / FR-016）。
 *
 * 页面范式与管理端统一：FilterBar 查询区 → 操作区 → el-table → el-pagination；
 * 详情与复杂操作一律 el-drawer（分区管理、临时关闭），轻量表单用 el-dialog（新增 / 编辑）。
 *
 * 关键口径（全部来自需求条文，未自行裁定）：
 * - FR-001：新增 / 修改 / 停用自习室与分区，维护名称、位置、开放时间与容量；
 *   本版**不提供物理删除**（Q-032：用「停用」代替删除，避免历史记录失去关联对象）。
 * - BR-019 / BR-022：场地临时关闭必须先列受影响预约清单 → 二次确认 → 才执行；
 *   确认前不得自动取消用户预约（清单与选择见 `RoomCloseDrawer.vue`）。
 * - NFR-009：所有写操作都提示「本次操作将记入审计日志」并收集原因。
 */
import { onMounted } from 'vue'

import AreaManageDrawer from '@/components/admin/AreaManageDrawer.vue'
import RoomCloseDrawer from '@/components/admin/RoomCloseDrawer.vue'
import RoomFormDialog from '@/components/admin/RoomFormDialog.vue'
import EmptyState from '@/components/EmptyState.vue'
import FilterBar from '@/components/FilterBar.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import { useRoomManage } from '@/utils/useRoomManage'

const {
  scopeLabel,
  directory,
  loading,
  refreshing,
  errorMessage,
  directoryFailed,
  keyword,
  enabledFilter,
  page,
  pageSize,
  total,
  paged,
  formVisible,
  editing,
  submitting,
  areaVisible,
  closeVisible,
  activeRoom,
  load,
  refresh,
  onSearch,
  onReset,
  onPageChange,
  onPageSizeChange,
  openCreate,
  openEdit,
  openAreas,
  openClose,
  submitForm,
  seatCount,
  areaCount,
} = useRoomManage()

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="自习室管理"
      subtitle="自习室与区域管理 · 座位信息维护 · 以「停用」代替物理删除；批量停用须先列清单再二次确认"
    />

    <FilterBar :loading="loading" @search="onSearch" @reset="onReset">
      <label class="filter-field">
        <span class="filter-field__label">名称 / 位置</span>
        <el-input
          v-model="keyword"
          class="w-200"
          clearable
          placeholder="如：第一自习室 / 图书馆"
          @keyup.enter="onSearch"
        />
      </label>
      <label class="filter-field">
        <span class="filter-field__label">启用状态</span>
        <el-select v-model="enabledFilter" class="w-120">
          <el-option label="全部" value="全部" />
          <el-option label="启用" value="启用" />
          <el-option label="停用" value="停用" />
        </el-select>
      </label>
    </FilterBar>

    <div class="admin-toolbar">
      <div class="admin-toolbar__buttons">
        <el-button type="primary" @click="openCreate">新增自习室</el-button>
        <el-button :loading="refreshing" @click="refresh()">刷新</el-button>
      </div>
      <span class="admin-toolbar__hint">操作范围：{{ scopeLabel }}</span>
    </div>

    <el-alert
      v-if="directoryFailed"
      class="notice"
      type="warning"
      :closable="false"
      show-icon
      title="座位与分区统计不可用"
    >
      <p>座位目录读取失败，表中「分区 / 座位」列显示为「—」；这不影响自习室本身的维护操作。</p>
    </el-alert>

    <section class="ssr-card">
      <LoadingBlock v-if="loading" :rows="5" text="正在读取自习室…" />

      <div v-else-if="errorMessage" class="panel">
        <el-alert type="error" :closable="false" show-icon title="自习室列表读取失败">
          <p>{{ errorMessage }}</p>
        </el-alert>
        <el-button type="primary" plain @click="load">重试</el-button>
      </div>

      <EmptyState
        v-else-if="paged.length === 0"
        :description="total === 0 ? '还没有自习室，请先新增一个' : '没有符合条件的自习室'"
        action-text="新增自习室"
        @action="openCreate"
      />

      <template v-else>
        <div class="table-wrap">
          <el-table :data="paged" size="small" border style="min-width: 980px">
            <el-table-column label="自习室名称" min-width="140">
              <template #default="{ row }">
                <strong>{{ row.name }}</strong>
                <div class="ssr-text-muted">编号 #{{ row.id }}</div>
              </template>
            </el-table-column>

            <el-table-column label="位置" min-width="160" prop="location" />

            <el-table-column label="开放时间" width="140">
              <template #default="{ row }">
                {{ row.open_time.slice(0, 5) }}–{{ row.close_time.slice(0, 5) }}
              </template>
            </el-table-column>

            <el-table-column label="容量" width="88" prop="capacity" />

            <el-table-column label="分区 / 座位" width="120">
              <template #default="{ row }">
                <span v-if="directoryFailed">—</span>
                <span v-else>{{ areaCount(row.id) }} 个分区 / {{ seatCount(row.id) }} 座</span>
              </template>
            </el-table-column>

            <el-table-column label="启用状态" width="100">
              <template #default="{ row }">
                <StatusTag kind="room" :value="row.enabled ? '启用' : '停用'" />
              </template>
            </el-table-column>

            <el-table-column label="操作" width="230" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openEdit(row)">编辑</el-button>
                <el-button link type="primary" size="small" @click="openAreas(row)">分区管理</el-button>
                <el-button link type="danger" size="small" @click="openClose(row)">临时关闭</el-button>
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
            :page-sizes="[10, 20, 50]"
            @current-change="onPageChange"
            @size-change="onPageSizeChange"
          />
        </div>
      </template>
    </section>

    <el-alert
      class="notice"
      type="info"
      :closable="false"
      show-icon
      title="关于「启用状态」与「临时关闭」的区别"
    >
      <p>
        「启用状态」只改自习室自身的标记，不影响座位是否可被预约，
        因此停用自习室不会让它的座位变成不可预约。
        「临时关闭」会先列出受影响的预约，再把范围内座位置为「停用」，
        可选的批量取消不计违约。两者语义不同，请按实际场景选择。
      </p>
    </el-alert>

    <RoomFormDialog
      v-model="formVisible"
      :room="editing"
      :submitting="submitting"
      :scope-label="scopeLabel"
      @submit="submitForm"
    />

    <AreaManageDrawer
      v-model="areaVisible"
      :room="activeRoom"
      :scope-label="scopeLabel"
      :directory="directory"
      @changed="refresh()"
    />

    <RoomCloseDrawer
      v-model="closeVisible"
      :room="activeRoom"
      :scope-label="scopeLabel"
      :directory="directory"
      @done="refresh()"
    />
  </div>
</template>

<style scoped>
.notice {
  margin-bottom: 12px;
}

.notice p {
  margin: 0;
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

.w-120 {
  width: 120px;
}
</style>


