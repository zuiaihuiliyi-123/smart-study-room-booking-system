<script setup lang="ts">
import { onMounted } from 'vue'

import PageHeader from '@/components/PageHeader.vue'
import ViolationSummary from '@/components/violations/ViolationSummary.vue'
import ViolationTable from '@/components/violations/ViolationTable.vue'
import { useMyViolations } from '@/utils/useMyViolations'

const {
  items,
  total,
  page,
  pageSize,
  loading,
  refreshing,
  errorMessage,
  focusId,
  threshold,
  count,
  remaining,
  percent,
  tone,
  progressStatus,
  accountStatus,
  restricted,
  disabled,
  restrictUntil,
  reservationLabel,
  operatorLabel,
  load,
  refresh,
  bootstrap,
  onPageChange,
} = useMyViolations()

onMounted(() => {
  void bootstrap()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="我的违约"
      subtitle="违规记录查询 · 账户状态；仅本人数据，不展示他人姓名"
    >
      <template #actions>
        <el-button :loading="refreshing" @click="refresh()">刷新</el-button>
        <el-button type="primary" plain @click="$router.push('/student/complaints')">
          提交问题反馈
        </el-button>
      </template>
    </PageHeader>

    <ViolationSummary
      :count="count"
      :threshold="threshold"
      :percent="percent"
      :progress-status="progressStatus"
      :tone="tone"
      :account-status="accountStatus"
      :restricted="restricted"
      :disabled="disabled"
      :restrict-until="restrictUntil"
      :remaining="remaining"
    />

    <section class="ssr-card">
      <header class="ssr-card__head">
        <h3>违约记录</h3>
        <span class="ssr-text-muted">
          共 {{ total }} 条 · 记录保留期限 1 年；本版不提供记录撤销与申诉入口（两项均已裁定排除）
        </span>
      </header>

      <ViolationTable
        :items="items"
        :loading="loading"
        :error-message="errorMessage"
        :focus-id="focusId"
        :reservation-label="reservationLabel"
        :operator-label="operatorLabel"
        @retry="load"
      />

      <div v-if="!loading && !errorMessage && total > 0" class="pager">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="total"
          :current-page="page"
          :page-size="pageSize"
          @current-change="onPageChange"
        />
      </div>
    </section>
  </div>
</template>

<style scoped>
.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}
</style>
