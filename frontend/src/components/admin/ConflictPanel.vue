<script setup lang="ts">
/**
 * BR-019 / BR-022 的「影响清单」面板。
 *
 * 需求依据（FR-016 / BR-019 / BR-022）：
 * - 场地临时关闭、座位转「维修中 / 停用」前，须**先列出**受影响的未来有效预约；
 * - **默认保留**冲突预约的状态（待使用 / 使用中），不自动取消，并持续提示；
 * - 只有管理员在清单中**明确选择批量取消**时才执行，且须二次确认；
 * - 批量取消**不计违约、不生成补偿、不支持改约**。
 *
 * 本组件只负责展示与收集「是否批量取消」的选择，不发起任何请求——执行时机由页面控制。
 */
import ReservationBriefTable from '@/components/admin/ReservationBriefTable.vue'
import type { Reservation } from '@/types'
import type { AdminDirectory } from '@/utils/adminData'

const props = withDefaults(
  defineProps<{
    reservations: Reservation[]
    loading?: boolean
    errorMessage?: string
    directory: AdminDirectory | null
    /** 是否已完成一次查询（区分「还没查」与「查了但没有受影响预约」） */
    queried?: boolean
    /** 是否提供「明确选择批量取消」的选项（仅 FR-016 的场地关闭场景） */
    allowCancel?: boolean
    cancelAffected?: boolean
  }>(),
  {
    loading: false,
    errorMessage: '',
    queried: false,
    allowCancel: false,
    cancelAffected: false,
  },
)

const emit = defineEmits<{
  (e: 'retry'): void
  (e: 'update:cancelAffected', value: boolean): void
}>()

function onCancelChange(value: boolean | string | number): void {
  emit('update:cancelAffected', value === true)
}
</script>

<template>
  <section class="conflict">
    <el-alert
      class="conflict__alert"
      type="warning"
      :closable="false"
      show-icon
      title="确认前不得自动取消用户预约"
    >
      <p class="conflict__line">
        受影响清单已列出。默认处理：<strong>仅变更座位资源状态</strong>，冲突预约保持「待使用 / 使用中」
        原状并在该座位、该时段上持续提示冲突，不生成违约记录。
      </p>
      <p class="conflict__line">
        只有你在下方<strong>明确勾选</strong>并二次确认后，系统才会批量取消：取消后
        <strong>不计违约、不累加违约次数、不生成补偿、不支持改约</strong>。
          </p>
        </el-alert>

        <p v-if="!props.queried" class="conflict__hint">
          尚未查询受影响预约。请先点「查询受影响预约」，系统会在列清清单后再允许执行。
        </p>

        <template v-else>
          <p class="conflict__count">
            受影响预约共 <strong>{{ props.reservations.length }}</strong> 条
            <span v-if="props.reservations.length === 0" class="ssr-text-muted">
              —— 没有预约受影响，可以安全执行
            </span>
          </p>

          <ReservationBriefTable
            :items="props.reservations"
            :loading="props.loading"
            :error-message="props.errorMessage"
            :directory="props.directory"
            empty-text="查询结果：该窗口内没有受影响的预约"
            max-height="260px"
            @retry="emit('retry')"
          />

          <el-checkbox
            v-if="props.allowCancel && props.reservations.length > 0"
            class="conflict__cancel"
            :model-value="props.cancelAffected"
            @update:model-value="onCancelChange"
          >
            我确认：同时<strong>批量取消</strong>上述 {{ props.reservations.length }} 条预约（不计违约、无补偿、不支持改约）
          </el-checkbox>
        </template>
      </section>
</template>

<style scoped>
.conflict {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
  background: var(--ssr-warning-bg);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.conflict__alert :deep(.el-alert__content) {
  color: var(--ssr-ink);
}

.conflict__line {
  margin: 2px 0 0;
  font-size: var(--ssr-font-note);
  line-height: 1.6;
}

.conflict__hint,
.conflict__count {
  margin: 0;
  font-size: var(--ssr-font-note);
  color: var(--ssr-ink);
}

.conflict__cancel {
  height: auto;
  white-space: normal;
}

.conflict__cancel :deep(.el-checkbox__label) {
  color: var(--ssr-danger);
  font-size: var(--ssr-font-note);
  line-height: 1.6;
  white-space: normal;
}
</style>
