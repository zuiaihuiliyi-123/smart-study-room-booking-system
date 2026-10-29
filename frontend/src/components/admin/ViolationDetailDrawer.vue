<script setup lang="ts">
/**
 * 违约记录详情抽屉（FR-032）。
 *
 * 只读：展示违约记录本身 + 关联预约单 + 登记来源（自动判定 / 手动登记及其操作人）。
 * 本页面明确不含导出（FR-033 已排除），也不提供「撤销违约」入口——FR-024 违约申诉已排除，
 * 撤销违约没有任何需求依据，因此不给入口（避免出现无依据的写操作）。
 */
import StatusTag from '@/components/StatusTag.vue'
import type { Violation } from '@/types'
import { operatorLabelOf, reservationLabelOf, userLabelOf, type AdminDirectory } from '@/utils/adminData'
import { formatDateTime } from '@/utils/format'

const props = defineProps<{
  modelValue: boolean
  violation: Violation | null
  directory: AdminDirectory | null
}>()

const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void }>()
</script>

<template>
  <el-drawer
    :model-value="props.modelValue"
    :title="props.violation === null ? '违约记录详情' : `违约记录详情 · #${props.violation.id}`"
    size="560px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template v-if="props.violation">
      <div class="head">
        <strong>#{{ props.violation.id }}</strong>
        <StatusTag kind="violation" :value="props.violation.type" />
      </div>

      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="用户">
          {{ userLabelOf(props.directory, props.violation.user_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="违约类型">
          {{ props.violation.type }}
          <span class="ssr-text-muted">
            {{
            props.violation.type === '自动违约'
            ? '（系统在签到截止后自动判定）'
            : '（管理员手动登记）'
            }}
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="违约原因">{{ props.violation.reason }}</el-descriptions-item>
        <el-descriptions-item label="关联预约单">
          {{ reservationLabelOf(props.directory, props.violation.reservation_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="登记人 / 判定来源">
          {{ operatorLabelOf(props.directory, props.violation.operator_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="记录时间">
          {{ formatDateTime(props.violation.created_at) }}
        </el-descriptions-item>
      </el-descriptions>

      <el-alert class="notice" type="info" :closable="false" show-icon title="处理说明">
        <p>
          违约记录只读：累计违约次数达到 3 次时系统会自动限制账户 7 天，
          限制到期自动解除（存在管理员手动限制时除外）。
        </p>
        <p>
          本版不提供「撤销违约」与「违约申诉」入口：违约申诉已按本版口径裁定排除；
          记录导出同样已排除，故本页没有导出按钮。
        </p>
      </el-alert>
    </template>
  </el-drawer>
</template>

<style scoped>
.head {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
  font-size: 15px;
}

.notice {
  margin-top: 12px;
}

.notice p {
  margin: 0 0 4px;
  font-size: var(--ssr-font-note);
  line-height: 1.6;
}
</style>
