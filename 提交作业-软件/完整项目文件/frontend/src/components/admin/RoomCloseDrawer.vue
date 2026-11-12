<script setup lang="ts">
/**
 * 场地临时关闭抽屉（FR-016 + BR-019 + BR-022）。
 *
 * 界面按需求条文分成三段：
 * 1. 关闭范围与窗口（只圈定受影响的预约，不改变任何数据）；
 * 2. 「查询受影响预约」→ 列出清单（`ConflictPanel`，只提示、不自动取消）；
 * 3. 「确认执行关闭」→ 二次确认（含审计提示）→ 才真正执行。
 *
 * 状态与流程全部在 `useRoomClose()` 里，本层只负责呈现。
 */
import { watch } from 'vue'
import dayjs from 'dayjs'

import AuditNotice from '@/components/admin/AuditNotice.vue'
import ConflictPanel from '@/components/admin/ConflictPanel.vue'
import type { Room } from '@/types'
import type { AdminDirectory } from '@/utils/adminData'
import { areaLabelOf } from '@/utils/adminData'
import { useRoomClose } from '@/utils/useRoomClose'

const props = defineProps<{
  modelValue: boolean
  room: Room | null
  scopeLabel: string
  directory: AdminDirectory | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'done'): void
}>()

const {
  areaId,
  dateRange,
  startTime,
  endTime,
  reason,
  queried,
  previewLoading,
  previewError,
  cancelAffected,
  executing,
  closures,
  closuresLoading,
  releasingId,
  areaOptions,
  windowError,
  reservations,
  open,
  invalidatePreview,
  preview,
  execute,
  releaseClosure,
} = useRoomClose()

watch(
  () => [props.modelValue, props.room?.id] as const,
  ([visible]) => {
    if (visible && props.room !== null) open(props.room, props.directory)
  },
  { immediate: true },
)

async function onExecute(): Promise<void> {
  if (await execute()) {
    emit('update:modelValue', false)
    emit('done')
  }
}

function formatRange(start: string, end: string): string {
  return `${dayjs(start).format('MM-DD HH:mm')} – ${dayjs(end).format('MM-DD HH:mm')}`
}

function areaNameOf(areaId: number): string {
  const label = areaLabelOf(props.directory, areaId)
  return label === '' ? '某个分区' : label
}
</script>

<template>
  <el-drawer
    :model-value="props.modelValue"
    :title="props.room === null ? '临时关闭' : `临时关闭 · ${props.room.name}`"
    size="640px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <AuditNotice
      :scope="props.scopeLabel"
      type="warning"
      :extra="'批量操作前会先列出影响清单；确认前不会自动取消任何用户预约。'"
    />

    <section v-if="closures.length > 0 || closuresLoading" class="ongoing">
      <div class="ongoing__head">
        <strong>进行中的临时关闭</strong>
        <span class="ssr-text-muted">到期自动失效，也可以提前解除</span>
      </div>
      <ul v-loading="closuresLoading" class="ongoing__list">
        <li v-for="item in closures" :key="item.id" class="ongoing__item">
          <div class="ongoing__main">
            <span class="ongoing__window">
              {{ formatRange(item.start_at, item.end_at) }}
            </span>
            <span class="ongoing__scope">
              {{ item.area_id === null || item.area_id === undefined ? '整个自习室' : areaNameOf(item.area_id) }}
            </span>
            <span class="ssr-text-muted ongoing__reason">{{ item.reason }}</span>
          </div>
          <el-button
            link
            type="primary"
            :loading="releasingId === item.id"
            @click="releaseClosure(item)"
          >
            提前解除
          </el-button>
        </li>
      </ul>
    </section>

    <el-form label-width="112px" @submit.prevent>
      <el-form-item label="关闭范围">
        <el-radio-group v-model="areaId" @change="invalidatePreview">
          <el-radio :value="0">整个自习室</el-radio>
          <el-radio v-for="area in areaOptions" :key="area.id" :value="area.id">
            {{ area.name }}
          </el-radio>
        </el-radio-group>
      </el-form-item>

      <el-form-item label="关闭日期">
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          @change="invalidatePreview"
        />
      </el-form-item>

      <el-form-item label="时段">
        <el-time-select
          v-model="startTime"
          class="time-select"
          start="00:00"
          step="00:30"
          end="23:30"
          aria-label="关闭窗口（开始）"
        />
        <span class="range-sep">至</span>
        <el-time-select
          v-model="endTime"
          class="time-select"
          start="00:30"
          step="00:30"
          end="23:30"
          aria-label="关闭窗口（结束）"
        />
        <p class="ssr-text-muted hint">关闭只在这段时间内生效，窗口结束后自动恢复，座位资源状态不变。</p>
      </el-form-item>

      <el-form-item v-if="windowError" label=" ">
        <el-alert type="error" :closable="false" show-icon :title="windowError" />
      </el-form-item>

      <el-form-item label="关闭原因">
        <el-input
          v-model="reason"
          type="textarea"
          :rows="2"
          maxlength="255"
          show-word-limit
          placeholder="如：线路检修，暂停开放（会写入审计日志）"
        />
      </el-form-item>
    </el-form>

    <div class="drawer-actions step">
      <el-button :loading="previewLoading" :disabled="windowError !== ''" @click="preview()">
        查询受影响预约
      </el-button>
      <span class="ssr-text-muted">查询不会改动任何数据。</span>
    </div>

    <ConflictPanel
      v-if="queried || previewError !== ''"
      :reservations="reservations"
      :loading="previewLoading"
      :error-message="previewError"
      :directory="props.directory"
      :queried="queried"
      allow-cancel
      :cancel-affected="cancelAffected"
      @update:cancelAffected="cancelAffected = $event"
      @retry="preview()"
    />

    <el-alert
      v-else
      class="notice"
      type="info"
      :closable="false"
      show-icon
      title="下一步：查询受影响预约"
    >
      <p>
        关闭期间该范围内的座位不可预约，窗口结束后自动恢复；受影响预约默认保留原状态，也可在下方勾选一并取消。
      </p>
    </el-alert>

    <template #footer>
      <div class="drawer-actions">
        <el-button @click="emit('update:modelValue', false)">取消</el-button>
        <el-button
          type="danger"
          :loading="executing"
          :disabled="!queried || windowError !== ''"
          @click="onExecute"
        >
          确认执行关闭
        </el-button>
      </div>
    </template>
  </el-drawer>
</template>

<style scoped>
.time-select {
  width: 128px;
}

.range-sep {
  padding: 0 8px;
  color: var(--ssr-muted-ink);
}

.hint {
  display: block;
  margin: 4px 0 0;
  line-height: 1.6;
}

.step {
  justify-content: flex-start;
  gap: 12px;
  padding-bottom: 12px;
}

.notice {
  margin-top: 4px;
}

.ongoing {
  margin: 4px 0 14px;
  padding: 10px 12px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius-sm);
}

.ongoing__head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 6px;
}

.ongoing__list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.ongoing__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 6px 0;
  border-top: 1px dashed var(--ssr-line);
}

.ongoing__item:first-child {
  border-top: 0;
}

.ongoing__main {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.ongoing__window {
  font-weight: 600;
}

.ongoing__scope {
  padding: 0 6px;
  color: var(--ssr-primary-ink);
  background: var(--ssr-primary-light);
  border-radius: 999px;
  font-size: calc(var(--ssr-font-note) - 1px);
}

.ongoing__reason {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 220px;
}

.notice p {
  margin: 0;
}
</style>


