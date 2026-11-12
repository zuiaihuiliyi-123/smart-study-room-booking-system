<script setup lang="ts">
/**
 * 用户管理（FR-040）。
 *
 * 查询口径：姓名 / 学号关键词 + 角色 + 账户状态 + 累计违约次数下限。
 * 管理员不可编辑姓名、学号等身份信息与口令，也不可代改联系方式。
 * 本版按 BR-018 收口：**学生账户**可停用/恢复、加入黑名单；管理员/系统管理员账号
 * 只读，由信息中心/系统管理员维护，本页不提供停用、恢复或黑名单入口。
 *
 * 页面只负责编排；筛选、表格与状态弹窗分别拆到 `components/admin/users/`。
 */
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import UserDetailDrawer from '@/components/admin/UserDetailDrawer.vue'
import UserManageFilters from '@/components/admin/users/UserManageFilters.vue'
import UserStatusDialog from '@/components/admin/users/UserStatusDialog.vue'
import UserTable from '@/components/admin/users/UserTable.vue'
import PageHeader from '@/components/PageHeader.vue'
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
  canManageAccount,
  canManageBlacklist,
  load,
  refresh,
  onSearch,
  onReset,
  onPageChange,
  onPageSizeChange,
  openDetail,
  statusDialogVisible,
  statusTarget,
  statusTargetValue,
  statusReason,
  statusSubmitting,
  statusError,
  openStatusDialog,
  closeStatusDialog,
  submitStatus,
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
      subtitle="查看用户信息；学生账户可停用/恢复与加入黑名单，管理员账号只读"
    />

    <UserManageFilters
      v-model:keyword="keyword"
      v-model:role-filter="roleFilter"
      v-model:status-filter="statusFilter"
      v-model:violation-min="violationMin"
      :loading="loading"
      @search="onSearch"
      @reset="onReset"
    />

    <div class="admin-toolbar">
      <div class="admin-toolbar__buttons">
        <el-button :loading="refreshing" @click="refresh()">刷新</el-button>
        <el-button type="primary" plain @click="goBlacklist">前往黑名单管理</el-button>
      </div>
      <span class="admin-toolbar__hint">操作范围：{{ scopeLabel }} · 共 {{ total }} 个用户</span>
    </div>

    <UserTable
      :items="items"
      :total="total"
      :loading="loading"
      :error-message="errorMessage"
      :page="page"
      :page-size="pageSize"
      :can-manage-account="canManageAccount"
      :can-manage-blacklist="canManageBlacklist"
      @retry="load"
      @detail="openDetail"
      @blacklist="openBlacklist"
      @status="openStatusDialog"
      @page-change="onPageChange"
      @page-size-change="onPageSizeChange"
    />

    <el-alert class="notice" type="info" :closable="false" show-icon title="本页可以做什么">
      <p>
        这里只能<strong>查询</strong>用户信息，不能修改姓名、学号、院系或密码；
        联系方式也只有用户本人能改，因此本页没有身份信息的编辑入口。
      </p>
      <p>
        列表中的手机号与邮箱只显示部分数字。对<strong>学生账户</strong>，
        <strong>受限</strong>由「黑名单管理」产生；<strong>停用 / 恢复</strong>可在本页操作
        （须填写原因并记入审计日志）。受限账户需先在黑名单解除限制，才能停用。
      </p>
      <p>
        <strong>管理员 / 系统管理员账号只读</strong>：由信息中心或系统管理员维护，
        本页不提供停用、恢复或黑名单入口。
      </p>
    </el-alert>

    <UserStatusDialog
      v-model="statusDialogVisible"
      v-model:reason="statusReason"
      :target="statusTarget"
      :target-value="statusTargetValue"
      :submitting="statusSubmitting"
      :error="statusError"
      @submit="submitStatus"
      @close="closeStatusDialog"
    />

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
</style>
