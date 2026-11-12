<script setup lang="ts">
import type { AuditLog } from '@/types'
import type { AdminDirectory } from '@/utils/adminData'
import { operatorLabelOf } from '@/utils/adminData'
import { actionLabel, prettyValue, targetLabel } from '@/utils/auditMeta'
import { formatDateTime } from '@/utils/format'

const visible = defineModel<boolean>({ required: true })

const props = defineProps<{
  detail: AuditLog | null
  directory: AdminDirectory | null
}>()
</script>

<template>
  <el-drawer v-model="visible" title="审计详情" size="520px">
    <template v-if="props.detail">
      <el-descriptions :column="1" border>
        <el-descriptions-item label="记录号">#{{ props.detail.id }}</el-descriptions-item>
        <el-descriptions-item label="操作时间">
          {{ formatDateTime(props.detail.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="操作人">
          {{ operatorLabelOf(props.directory, props.detail.operator_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="操作类型">
          {{ actionLabel(props.detail.action_type) }}（{{ props.detail.action_type }}）
        </el-descriptions-item>
        <el-descriptions-item label="目标">
          {{ targetLabel(props.directory, props.detail) }}
        </el-descriptions-item>
        <el-descriptions-item label="原因 / 说明">
          {{ props.detail.reason || '—' }}
        </el-descriptions-item>
      </el-descriptions>

      <section class="detail-block">
        <h4>变更前</h4>
        <pre class="detail-value">{{ prettyValue(props.detail.before_value) }}</pre>
      </section>
      <section class="detail-block">
        <h4>变更后</h4>
        <pre class="detail-value">{{ prettyValue(props.detail.after_value) }}</pre>
      </section>

      <p class="ssr-text-muted detail-note">
        审计记录只读；本抽屉仅展示数据库中的原始内容，不执行任何修改操作。
      </p>
    </template>
  </el-drawer>
</template>

<style scoped>
.detail-block {
  margin-top: 16px;
}

.detail-block h4 {
  margin: 0 0 6px;
  color: var(--ssr-ink);
  font-size: 13px;
  font-weight: 600;
}

.detail-value {
  max-height: 220px;
  padding: 10px 12px;
  margin: 0;
  overflow: auto;
  color: var(--ssr-ink);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  background: var(--ssr-bg);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius-sm);
}

.detail-note {
  margin: 14px 0 0;
  line-height: 1.6;
}
</style>
