<script setup lang="ts">
import { onMounted } from 'vue'

import ComplaintForm from '@/components/complaints/ComplaintForm.vue'
import ComplaintList from '@/components/complaints/ComplaintList.vue'
import type { TargetType } from '@/components/complaints/complaintMeta'
import PageHeader from '@/components/PageHeader.vue'
import { useMyComplaints } from '@/utils/useMyComplaints'

const {
  items,
  total,
  page,
  pageSize,
  loading,
  errorMessage,
  submitting,
  confirmingId,
  newId,
  focusId,
  rooms,
  seats,
  reservations,
  load,
  submit,
  confirmClose,
  bootstrap,
  onPageChange,
} = useMyComplaints()

function onSubmit(payload: { target_type: TargetType; target_id: number; content: string }): void {
  void submit(payload)
}

onMounted(() => {
  void bootstrap()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="我的投诉"
      subtitle="投诉提交 · 处理进度与反馈；投诉对象为座位 / 自习室 / 预约单 / 用户 4 类"
    >
      <template #actions>
        <el-button :loading="loading" @click="load">刷新列表</el-button>
      </template>
    </PageHeader>

    <div class="grid">
      <ComplaintForm
        :rooms="rooms"
        :seats="seats"
        :reservations="reservations"
        :submitting="submitting"
        @submit="onSubmit"
      />

      <section class="ssr-card">
        <header class="ssr-card__head">
          <h3>我的投诉</h3>
          <span class="ssr-text-muted">共 {{ total }} 条 · 按提交时间倒序</span>
        </header>

        <ComplaintList
          :items="items"
          :loading="loading"
          :error-message="errorMessage"
          :new-id="newId"
          :focus-id="focusId"
          :confirming-id="confirmingId"
          @retry="load"
          @confirm="confirmClose"
        />

        <div v-if="!loading && !errorMessage && total > pageSize" class="pager">
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
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-columns: minmax(0, 420px) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

@media (max-width: 1024px) {
  .grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
