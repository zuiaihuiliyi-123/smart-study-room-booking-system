<script setup lang="ts">
/**
 * 用户管理（FR-040）。
 *
 * 查询口径：姓名 / 学号关键词 + 角色 + 账户状态 + 累计违约次数下限。
 * **只读页面**：按 BR-018 / Q-030 的本版裁定，管理员不可编辑姓名、学号等身份信息与口令，
 * 也不可代改联系方式，因此本页没有任何编辑入口；账户状态变更一律走「黑名单管理」（FR-044），
 * 表格与详情抽屉都提供跳转入口。
 *
 * NFR-006：手机号 / 邮箱一律掩码展示。
 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import UserDetailDrawer from '@/components/admin/UserDetailDrawer.vue'
import EmptyState from '@/components/EmptyState.vue'
import FilterBar from '@/components/FilterBar.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import { contactKindLabel, maskContact } from '@/utils/mask'
import { useUserManage } from '@/utils/useUserManage'

const router = useRouter()

const {
  scopeLabel,
  items,
  total,
  loading,
  refreshing,
  errorMessage,
  keyword,
  roleFilter,
  statusFilter,
  violationMin,
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
} = useUserManage()

function openBlacklist(userId: number, name: string): void {
  void router.push({
    name: 'admin-blacklist',
    query: { user_id: String(userId), user_name: name },
  })
}

/** 不带用户过滤，直接进入黑名单管理 */
function goBlacklist(): void {
  void router.push({ name: 'admin-blacklist' })
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="用户管理"
      subtitle="用户信息查询 · 只读：不可编辑姓名 / 学号与口令 · 手机号与邮箱一律掩码"
    />

    <FilterBar :loading="loading" @search="onSearch" @reset="onReset">
      <label class="filter-field">
        <span class="filter-field__label">姓名 / 学号</span>
        <el-input
          v-model="keyword"
          class="w-190"
          clearable
          placeholder="如：李明 / 3200104523"
          @keyup.enter="onSearch"
        />
      </label>

      <label class="filter-field">
        <span class="filter-field__label">角色</span>
        <el-select v-model="roleFilter" class="w-150">
          <el-option label="全部" value="全部" />
          <el-option label="学生用户" value="学生用户" />
          <el-option label="教师用户" value="教师用户" />
          <el-option label="自习室管理员" value="自习室管理员" />
          <el-option label="系统管理员" value="系统管理员" />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">账户状态</span>
        <el-select v-model="statusFilter" class="w-130">
          <el-option label="全部" value="全部" />
          <el-option label="正常" value="正常" />
          <el-option label="受限" value="受限" />
          <el-option label="停用" value="停用" />
        </el-select>
      </label>

      <label class="filter-field">
        <span class="filter-field__label">累计违约 ≥</span>
        <el-input-number v-model="violationMin" class="w-130" :min="0" :max="99" :step="1" />
      </label>
    </FilterBar>

    <div class="admin-toolbar">
      <div class="admin-toolbar__buttons">
        <el-button :loading="refreshing" @click="refresh()">刷新</el-button>
        <el-button type="primary" plain @click="goBlacklist">前往黑名单管理</el-button>
      </div>
      <span class="admin-toolbar__hint">操作范围：{{ scopeLabel }} · 共 {{ total }} 个用户</span>
    </div>

    <section class="ssr-card">
      <LoadingBlock v-if="loading" :rows="6" text="正在读取用户…" />

      <div v-else-if="errorMessage" class="panel">
        <el-alert type="error" :closable="false" show-icon title="用户列表读取失败">
          <p>{{ errorMessage }}</p>
        </el-alert>
        <el-button type="primary" plain @click="load">重试</el-button>
      </div>

      <EmptyState
        v-else-if="items.length === 0"
        description="当前筛选条件下没有用户。可清空角色 / 账户状态 / 违约次数筛选后再查"
      />

      <template v-else>
        <div class="table-wrap">
          <el-table :data="items" size="small" border style="min-width: 1080px">
            <el-table-column label="用户" min-width="170">
              <template #default="{ row }">
                <el-button link type="primary" @click="openDetail(row)">{{ row.name }}</el-button>
                <div class="ssr-text-muted">#{{ row.id }}</div>
              </template>
            </el-table-column>

            <el-table-column label="学号 / 工号" width="140" prop="student_no" />

            <el-table-column label="角色" width="130" prop="role" />

            <el-table-column label="账户状态" width="110">
              <template #default="{ row }">
                <StatusTag kind="account" :value="row.account_status" />
              </template>
            </el-table-column>

            <el-table-column label="累计违约次数" width="130">
              <template #default="{ row }">
                <span :class="{ 'violation-alert': row.violation_count >= 3 }">
                  {{ row.violation_count }} / 3
                </span>
              </template>
            </el-table-column>

            <el-table-column label="联系方式（已掩码）" min-width="200">
              <template #default="{ row }">
                <div>{{ maskContact(row.contact) }}</div>
                <div class="ssr-text-muted">{{ contactKindLabel(row.contact) }} · 掩码</div>
              </template>
            </el-table-column>

            <el-table-column label="预计解除时间" min-width="150">
              <template #default="{ row }">
                <span v-if="row.restrict_until">{{ row.restrict_until }}</span>
                <span v-else class="ssr-text-muted">待后端提供接口</span>
              </template>
            </el-table-column>

            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="openDetail(row)">详情</el-button>
                <el-button
                  link
                  type="warning"
                  size="small"
                  @click="openBlacklist(row.id, row.name)"
                >
                  黑名单
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

    <el-alert class="notice" type="info" :closable="false" show-icon title="权限与脱敏口径">
      <p>
        + 管理员<strong>仅可查询</strong>用户信息，<strong>不可编辑</strong>姓名、学号、院系等身份信息与口令；
        联系方式是用户唯一可自行修改的字段，管理员亦不得代改。因此本页没有任何编辑入口。
      </p>
      <p>
        列表中手机号与邮箱一律掩码（本页掩码逻辑集中在 <code>utils/mask.ts</code>）。
        账户状态变更不在此页执行，请到「黑名单管理」页面处理。
      </p>
    </el-alert>

    <UserDetailDrawer
      v-model="detailVisible"
      :user="detail"
      @open-blacklist="(userId) => openBlacklist(userId, detail?.name ?? '')"
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

.notice code {
  padding: 0 4px;
  font-size: var(--ssr-font-note);
  background: var(--ssr-primary-light);
  border-radius: 4px;
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

.violation-alert {
  color: var(--ssr-danger);
  font-weight: 600;
}

.w-190 {
  width: 190px;
}
</style>


