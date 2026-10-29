<script setup lang="ts">
/**
 * 座位资源状态调整抽屉（FR-004 + BR-019 + BR-022）。
 *
 * 流程与需求条文对应：
 * 1. 选择目标资源状态（可用 / 维修中 / 停用）并填写原因（必填，NFR-009 留痕）；
 * 2. 点「查询冲突预约」→ 列出与该窗口冲突的有效预约（只读，BR-019 只提示、不自动取消）；
 * 3. 点「确认调整」→ 二次确认（含审计提示）→ 执行批量调整。
 *
 * 注意 `seat.status` 只承载**资源状态**；「该时段占用」是另一维度，本抽屉不写入。
 */
import { computed } from 'vue'

import AuditNotice from '@/components/admin/AuditNotice.vue'
import ConflictPanel from '@/components/admin/ConflictPanel.vue'
import { seatLabelOf, type AdminDirectory } from '@/utils/adminData'
import type { Reservation, Seat } from '@/types'

const props = defineProps<{
  modelValue: boolean
  scopeLabel: string
  directory: AdminDirectory | null
  seats: Seat[]
  targetStatus: Seat['status']
  reason: string
  conflictFrom: string
  conflictTo: string
  conflicts: Reservation[]
  conflictsQueried: boolean
  conflictLoading: boolean
  conflictError: string
  executing: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'update:targetStatus', value: Seat['status']): void
  (e: 'update:reason', value: string): void
  (e: 'update:conflictFrom', value: string): void
  (e: 'update:conflictTo', value: string): void
  (e: 'check'): void
  (e: 'execute'): void
}>()

const STATUS_OPTIONS: readonly Seat['status'][] = ['可用', '维修中', '停用']

const title = computed(() => `调整座位资源状态 · 已选 ${props.seats.length} 个座位`)

const windowError = computed(() =>
    props.conflictTo <= props.conflictFrom ? '调整窗口不合法：结束时刻必须晚于开始时刻' : '',
)

const summary = computed(() =>
    props.seats.map((seat) => seatLabelOf(props.directory, seat)).join('、'),
)
</script>

<template>
  <el-drawer
    :model-value="props.modelValue"
    :title="title"
    size="620px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <AuditNotice
      :scope="props.scopeLabel"
      :extra="'座位资源状态在「可用 / 维修中 / 停用」之间转换，不改变任何预约单的状态。'"
    />

    <section class="ssr-card block">
      <h4 class="drawer-section">已选座位（{{ props.seats.length }}）</h4>
      <p class="drawer-note">{{ summary }}</p>
    </section>

    <el-form label-width="96px" @submit.prevent>
      <el-form-item label="目标状态">
        <el-radio-group
          :model-value="props.targetStatus"
          @update:model-value="emit('update:targetStatus', $event)"
        >
          <el-radio v-for="status in STATUS_OPTIONS" :key="status" :value="status">
            {{ status }}
          </el-radio>
        </el-radio-group>
        <p class="ssr-text-muted hint">
          「可用」= 可被预约；「维修中」「停用」= 不可被预约。
        </p>
      </el-form-item>

      <el-form-item label="调整原因">
        <el-input
          :model-value="props.reason"
          type="textarea"
          :rows="2"
          maxlength="255"
          show-word-limit
          placeholder="如：台灯损坏，转维修中并通知物业"
          @update:model-value="emit('update:reason', $event)"
        />
      </el-form-item>

      <el-form-item label="影响窗口">
        <el-date-picker
          :model-value="props.conflictFrom"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm"
          placeholder="窗口开始"
          aria-label="影响窗口（开始）"
          class="w-datetime"
          @update:model-value="emit('update:conflictFrom', String($event ?? ''))"
        />
        <span class="range-sep">至</span>
        <el-date-picker
          :model-value="props.conflictTo"
          type="datetime"
          value-format="YYYY-MM-DDTHH:mm"
          placeholder="窗口结束（不含）"
          aria-label="影响窗口（结束，不含）"
          class="w-datetime"
          @update:model-value="emit('update:conflictTo', String($event ?? ''))"
        />
        <p class="ssr-text-muted hint">
          该窗口只用于圈定「冲突的有效预约」（待使用 / 使用中），默认覆盖未来 7 天。
        </p>
      </el-form-item>

      <el-form-item v-if="windowError" label=" ">
        <el-alert type="error" :closable="false" show-icon :title="windowError" />
      </el-form-item>
    </el-form>

    <div class="drawer-actions step">
      <el-button :loading="props.conflictLoading" :disabled="windowError !== ''" @click="emit('check')">
        查询冲突预约
      </el-button>
      <span class="ssr-text-muted">
        查询是只读操作；调整前必须先查看冲突清单再决定，系统不会自动取消任何预约。
      </span>
    </div>

    <ConflictPanel
      v-if="props.conflictsQueried || props.conflictError !== ''"
      :reservations="props.conflicts"
      :loading="props.conflictLoading"
      :error-message="props.conflictError"
      :directory="props.directory"
      :queried="props.conflictsQueried"
      @retry="emit('check')"
    />

    <template #footer>
      <div class="drawer-actions">
        <el-button @click="emit('update:modelValue', false)">取消</el-button>
        <el-button
          type="primary"
          :loading="props.executing"
          :disabled="windowError !== ''"
          @click="emit('execute')"
        >
          确认调整
        </el-button>
      </div>
    </template>
  </el-drawer>
</template>

<style scoped>
.block {
  margin-bottom: 12px;
}

.hint {
  display: block;
  margin: 4px 0 0;
  line-height: 1.6;
}

.range-sep {
  padding: 0 8px;
  color: var(--ssr-muted-ink);
}

.step {
  justify-content: flex-start;
  gap: 12px;
  padding-bottom: 12px;
}
</style>



