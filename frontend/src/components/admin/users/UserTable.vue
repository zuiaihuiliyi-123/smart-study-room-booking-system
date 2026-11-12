<script setup lang="ts">
import EmptyState from '@/components/EmptyState.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import StatusTag from '@/components/StatusTag.vue'
import type { CurrentUser } from '@/types'
import { contactKindLabel, maskContact } from '@/utils/mask'

const props = defineProps<{
  items: CurrentUser[]
  total: number
  loading: boolean
  errorMessage: string
  page: number
  pageSize: number
  /** BR-018：业务管理员只能维护学生账户，管理员账号只读 */
  canManageAccount: (item: CurrentUser) => boolean
  canManageBlacklist: (item: CurrentUser) => boolean
}>()

const emit = defineEmits<{
  (e: 'retry'): void
  (e: 'detail', item: CurrentUser): void
  (e: 'blacklist', userId: number, name: string): void
  (e: 'status', item: CurrentUser): void
  (e: 'page-change', page: number): void
  (e: 'page-size-change', size: number): void
}>()

function onPageChange(value: number): void {
  emit('page-change', value)
}

function onPageSizeChange(value: number): void {
  emit('page-size-change', value)
}
</script>

<template>
  <section class="ssr-card">
    <LoadingBlock v-if="props.loading" :rows="6" text="正在读取用户…" />

    <div v-else-if="props.errorMessage" class="panel">
      <el-alert type="error" :closable="false" show-icon title="用户列表读取失败">
        <p>{{ props.errorMessage }}</p>
      </el-alert>
      <el-button type="primary" plain @click="emit('retry')">重试</el-button>
    </div>

    <EmptyState
      v-else-if="props.items.length === 0"
      description="当前筛选条件下没有用户。可清空角色 / 账户状态 / 违约次数筛选后再查"
    />

    <template v-else>
      <div class="table-wrap">
        <el-table :data="props.items" size="small" border style="min-width: 1080px">
          <el-table-column label="用户" min-width="170">
            <template #default="{ row }">
              <el-button link type="primary" @click="emit('detail', row)">{{ row.name }}</el-button>
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
              <span
                v-if="row.role === '学生用户'"
                :class="{ 'violation-alert': row.violation_count >= 3 }"
              >
                {{ row.violation_count }} / 3
              </span>
              <span v-else class="ssr-text-muted">不适用</span>
            </template>
          </el-table-column>

          <el-table-column label="联系方式" min-width="200">
            <template #default="{ row }">
              <div>{{ maskContact(row.contact) }}</div>
              <div class="ssr-text-muted">{{ contactKindLabel(row.contact) }}</div>
            </template>
          </el-table-column>

          <el-table-column label="预计解除时间" min-width="150">
            <template #default="{ row }">
              <span v-if="row.account_status !== '受限'" class="ssr-text-muted">—</span>
              <span v-else-if="row.restrict_until">{{ row.restrict_until }}</span>
              <span v-else class="ssr-text-muted">手动限制，无自动解除时间</span>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="300" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="emit('detail', row)">
                详情
              </el-button>

              <template v-if="props.canManageAccount(row)">
                <el-button
                  v-if="props.canManageBlacklist(row)"
                  link
                  type="warning"
                  size="small"
                  @click="emit('blacklist', row.id, row.name)"
                >
                  黑名单
                </el-button>
                <el-button
                  v-if="row.account_status === '正常'"
                  link
                  type="danger"
                  size="small"
                  @click="emit('status', row)"
                >
                  停用
                </el-button>
                <el-button
                  v-else-if="row.account_status === '停用'"
                  link
                  type="success"
                  size="small"
                  @click="emit('status', row)"
                >
                  恢复
                </el-button>
                <el-button v-else link size="small" disabled>受限中</el-button>
              </template>

              <span v-else class="ssr-text-muted">管理员账号由信息中心维护</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <div class="pager" role="navigation" aria-label="分页">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next"
          :total="props.total"
          :current-page="props.page"
          :page-size="props.pageSize"
          :page-sizes="[20, 50, 100]"
          @current-change="onPageChange"
          @size-change="onPageSizeChange"
        />
      </div>
    </template>
  </section>
</template>

<style scoped>
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
</style>
