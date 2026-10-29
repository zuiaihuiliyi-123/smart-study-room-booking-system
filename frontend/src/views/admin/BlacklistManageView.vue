<script setup lang="ts">
/**
 * 黑名单管理（FR-044 + BR-009 / BR-010 / ST-041～ST-043）。
 *
 * 列表口径：用户、原因、来源（自动 / 手动）、加入时间、期限、解除时间、操作者、当前状态。
 * 两类写操作：手动加入（`BlacklistAddDialog`，必填原因 + 期限）、手动解除
 * （`BlacklistDetailDrawer` 内就地填写原因），两者都提示「本次操作将记入审计日志」（NFR-009）。
 *
 * 必须显式说明的口径：**存在管理员手动限制时系统不得自动解除**（BR-010 / ST-042），
 * 因此「不设期限」的手动记录只会一直生效，直到管理员手动解除。
 */
import { onMounted } from 'vue'
import { useRoute } from 'vue-router'

import BlacklistAddDialog from '@/components/admin/BlacklistAddDialog.vue'
import BlacklistDetailDrawer from '@/components/admin/BlacklistDetailDrawer.vue'
import EmptyState from '@/components/EmptyState.vue'
import FilterBar from '@/components/FilterBar.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import { operatorLabelOf, userLabelOf } from '@/utils/adminData'
import { formatDateTime } from '@/utils/format'
import { useBlacklistManage } from '@/utils/useBlacklistManage'

const route = useRoute()

const {
  scopeLabel,
  directory,
  items,
  total,
  loading,
  refreshing,
  errorMessage,
  stateFilter,
  modeFilter,
  userId,
  userIdLabel,
  studentNoInput,
  filteredByUser,
  page,
  pageSize,
  addVisible,
  detailVisible,
  detail,
  submitting,
  load,
  refresh,
  onSearch,
  onReset,
  applyQuery,
  onPageChange,
  onPageSizeChange,
  openAdd,
  openDetail,
  onSearchByStudentNo,
  add,
  release,
  stateOf,
  expireText,
} = useBlacklistManage()

function clearUserFilter(): void {
  userId.value = null
  userIdLabel.value = ''
  studentNoInput.value = ''
  page.value = 1
  void load()
}

onMounted(() => {
  applyQuery(route.query as Record<string, string>)
  void load()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="黑名单管理"
      subtitle="黑名单查询 / 手动加入 / 手动解除 · 存在管理员手动限制时系统不得自动解除"
    />

    <FilterBar :loading="loading" @search="onSearch" @reset="onReset">
      <label class="filter-field">
        <span class="filter-field__label">状态</span>
        <el-select v-model="stateFilter" class="w-130">
          <el-option label="生效中" value="生效中" />
          <el-option label="已解除" value="已解除" />
          <el-option label="已过期" value="已过期" />
          <el-option label="全部" value="全部" />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">来源</span>
        <el-select v-model="modeFilter" class="w-120">
          <el-option label="全部" value="全部" />
          <el-option label="自动" value="自动" />
          <el-option label="手动" value="手动" />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">按学号定位</span>
        <el-input
          v-model="studentNoInput"
          class="w-170"
          clearable
          placeholder="如：3200104523"
          @keyup.enter="onSearchByStudentNo"
        />
        <el-button @click="onSearchByStudentNo">定位用户</el-button>
      </label>
    </FilterBar>

    <div class="admin-toolbar">
      <div class="admin-toolbar__buttons">
        <el-button type="primary" @click="openAdd">手动加入黑名单</el-button>
        <el-button :loading="refreshing" @click="refresh()">刷新</el-button>
        <el-tag v-if="filteredByUser" class="ssr-tag ssr-tag--primary" closable disable-transitions @close="clearUserFilter">
          仅看用户 {{ userIdLabel === '' ? `#${userId}` : `${userIdLabel}（#${userId}）` }}
        </el-tag>
      </div>
      <span class="admin-toolbar__hint">操作范围：{{ scopeLabel }} · 共 {{ total }} 条记录</span>
    </div>

    <el-alert class="notice" type="warning" :closable="false" show-icon title="自动解除的边界">
      <p>
        限制期满后系统会自动解除账户限制，条件是<strong>该账户不存在其它生效中的限制</strong>。
        若存在<strong>管理员手动设置</strong>且仍生效的限制，系统<strong>不得</strong>自动解除，必须由管理员手动解除。
      </p>
      <p>
        「不设期限」的手动记录因此会一直生效，直到管理员手动解除——列表中已标注「不设期限（仅可手动解除）」。
      </p>
    </el-alert>

    <section class="ssr-card">
      <LoadingBlock v-if="loading" :rows="6" text="正在读取黑名单…" />

      <div v-else-if="errorMessage" class="panel">
        <el-alert type="error" :closable="false" show-icon title="黑名单读取失败">
          <p>{{ errorMessage }}</p>
        </el-alert>
        <el-button type="primary" plain @click="load">重试</el-button>
      </div>

      <EmptyState
        v-else-if="items.length === 0"
        description="当前筛选条件下没有黑名单记录。默认只看「生效中」，可切换状态或按学号定位用户"
      />

      <template v-else>
        <div class="table-wrap">
          <el-table :data="items" size="small" border style="min-width: 1240px">
            <el-table-column label="记录号" width="92">
              <template #default="{ row }">
                <el-button link type="primary" @click="openDetail(row)">#{{ row.id }}</el-button>
              </template>
            </el-table-column>

            <el-table-column label="用户" min-width="170">
              <template #default="{ row }">{{ userLabelOf(directory, row.user_id) }}</template>
            </el-table-column>

            <el-table-column label="限制原因" min-width="200">
              <template #default="{ row }">{{ row.reason }}</template>
            </el-table-column>

            <el-table-column label="来源" width="90">
              <template #default="{ row }">
                <StatusTag kind="blacklist" :value="row.mode" />
              </template>
            </el-table-column>

            <el-table-column label="状态" width="96">
              <template #default="{ row }">
                <StatusTag kind="blacklistState" :value="stateOf(row)" />
              </template>
            </el-table-column>

            <el-table-column label="加入时间" width="150">
              <template #default="{ row }">{{ formatDateTime(row.start_at) }}</template>
            </el-table-column>

            <el-table-column label="限制期限" min-width="170">
              <template #default="{ row }">{{ expireText(row) }}</template>
            </el-table-column>

            <el-table-column label="解除时间" width="150">
              <template #default="{ row }">{{ formatDateTime(row.released_at) }}</template>
            </el-table-column>

            <el-table-column label="操作者" min-width="150">
              <template #default="{ row }">
                {{ row.operator_id === null ? '系统自动' : operatorLabelOf(directory, row.operator_id) }}
              </template>
            </el-table-column>

            <el-table-column label="操作" width="110" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openDetail(row)">
                  {{ row.released_at === null ? '解除 / 详情' : '详情' }}
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

    <el-alert class="notice" type="info" :closable="false" show-icon title="脱敏与留痕">
      <p>
        本页只展示用户姓名与学号用于辨识（管理员可查询用户信息）；手机号与邮箱不在此页出现，
        如需查看请在「用户管理」中以掩码形式查看。
      </p>
      <p>
        加入与解除限制都会记入审计日志：记录操作者、时间与原因；黑名单记录保留 1 年，
        本版不提供导出。
      </p>
    </el-alert>

    <BlacklistAddDialog
      v-model="addVisible"
      :directory="directory"
      :scope-label="scopeLabel"
      :submitting="submitting"
      @submit="add"
    />

    <BlacklistDetailDrawer
      v-model="detailVisible"
      :entry="detail"
      :directory="directory"
      :scope-label="scopeLabel"
      :submitting="submitting"
      @release="release"
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

.w-170 {
  width: 170px;
}
</style>



