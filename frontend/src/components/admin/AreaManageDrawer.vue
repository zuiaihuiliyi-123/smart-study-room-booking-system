<script setup lang="ts">
/**
 * 分区管理抽屉（FR-001：自习室内部的分区）。
 *
 * SCOPE-06 本版裁定：分区**不是**独立的资源管理层级，只作为自习室内部的座位分组属性
 * （用于座位展示与筛选），不承担任何权限范围划分——因此这里只做「查看 + 新增」，
 * 不提供分区级授权、不提供删除（座位仍挂在分区下，删除会造成孤儿引用）。
 *
 * 接口现状：`GET /rooms/{id}/areas` 后端尚未实现，取不到时按座位号前缀推断名称并明确标注。
 */
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'

import { createArea, listAreas } from '@/api/room'
import AuditNotice from '@/components/admin/AuditNotice.vue'
import EmptyState from '@/components/EmptyState.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import type { Area, Room } from '@/types'
import { invalidateAdminDirectory, type AdminDirectory } from '@/utils/adminData'
import { toBookingFailure } from '@/utils/bookingData'

const props = defineProps<{
  modelValue: boolean
  room: Room | null
  scopeLabel: string
  directory: AdminDirectory | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'changed'): void
}>()

const areas = ref<Area[]>([])
const loading = ref(false)
const errorMessage = ref('')
const newName = ref('')
const reason = ref('')
const submitting = ref(false)

const title = computed(() =>
    props.room === null ? '分区管理' : `分区管理 · ${props.room.name}`,
)

/** 分区名称缺失时（后端未提供列表接口）用座位号前缀兜底，和座位页保持同一口径 */
const fallbackAreas = computed<Area[]>(() => {
  if (props.room === null) return []
  const seats = props.directory?.seatsByRoom.get(props.room.id) ?? []
  const ids = [...new Set(seats.map((seat) => seat.area_id).filter((id): id is number => id !== null))]
  return ids
    .filter((id) => !areas.value.some((area) => area.id === id))
    .map((id) => ({ id, room_id: props.room?.id ?? 0, name: `分区 #${id}（名称待后端提供接口）` }))
})

const rows = computed(() => [...areas.value, ...fallbackAreas.value])

function seatCount(areaId: number): number {
  const seats = props.directory?.seatsByRoom.get(props.room?.id ?? 0) ?? []
  return seats.filter((seat) => seat.area_id === areaId).length
}

async function load(): Promise<void> {
  if (props.room === null) return
  loading.value = true
  errorMessage.value = ''
  try {
    areas.value = await listAreas(props.room.id)
  } catch (caught) {
    errorMessage.value = toBookingFailure(caught).message
    areas.value = []
  } finally {
    loading.value = false
  }
}

watch(
  () => props.modelValue,
  (visible) => {
    if (!visible) return
    newName.value = ''
    reason.value = ''
    void load()
  },
)

async function onAdd(): Promise<void> {
  if (props.room === null) return
  if (newName.value.trim() === '') {
    ElMessage.warning('请填写分区名称')
    return
  }
  if (reason.value.trim() === '') {
    ElMessage.warning('请填写新增分区的说明：该说明会写入审计日志')
    return
  }
  submitting.value = true
  try {
    const area = await createArea(props.room.id, newName.value.trim(), reason.value.trim())
    ElMessage.success(`分区「${area.name}」已创建，可在「座位管理」中为其新增座位`)
    newName.value = ''
    reason.value = ''
    invalidateAdminDirectory()
    await load()
    emit('changed')
  } catch (caught) {
    ElMessage.error(toBookingFailure(caught).message)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <el-drawer
    :model-value="props.modelValue"
    :title="title"
    size="520px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <AuditNotice
      :scope="props.scopeLabel"
      :extra="'分区仅作为自习室内部的座位分组属性（不构成独立资源层级，不划分权限范围）。'"
    />

    <el-alert
      v-if="errorMessage !== ''"
      class="notice"
      type="warning"
      :closable="false"
      show-icon
      title="分区列表接口不可用"
    >
      <p>{{ errorMessage }}</p>
      <p>
        后端目前只有「新增分区」，没有 `GET /rooms/{room_id}/areas`；下方按座位号前缀推断的分区
        已明确标注，未编造名称。接口补齐后自动显示真实名称。
      </p>
    </el-alert>

    <h4 class="drawer-section">已有分区（{{ rows.length }}）</h4>
    <LoadingBlock v-if="loading" :rows="3" text="正在读取分区…" />
    <EmptyState v-else-if="rows.length === 0" description="该自习室还没有分区，可在下方新增" :image-size="60" />
    <div v-else class="table-wrap">
      <el-table :data="rows" size="small" border style="min-width: 360px">
        <el-table-column label="分区" min-width="220">
          <template #default="{ row }">{{ row.name }}</template>
        </el-table-column>
        <el-table-column label="分区编号" width="96">
          <template #default="{ row }">#{{ row.id }}</template>
        </el-table-column>
        <el-table-column label="座位数" width="88">
          <template #default="{ row }">{{ seatCount(row.id) }}</template>
        </el-table-column>
      </el-table>
    </div>

    <h4 class="drawer-section">新增分区</h4>
    <el-form label-width="88px" @submit.prevent>
      <el-form-item label="分区名称">
        <el-input v-model="newName" maxlength="50" show-word-limit placeholder="如：静音区 / 靠窗区 / 电源区" />
      </el-form-item>
      <el-form-item label="变更说明">
        <el-input
          v-model="reason"
          type="textarea"
          :rows="2"
          maxlength="255"
          show-word-limit
          placeholder="如：新增电源区，供带电脑的同学使用"
        />
      </el-form-item>
    </el-form>

    <div class="drawer-actions">
      <el-button @click="emit('update:modelValue', false)">关闭</el-button>
      <el-button type="primary" :loading="submitting" @click="onAdd">新增分区</el-button>
    </div>
  </el-drawer>
</template>

<style scoped>
.notice {
  margin-bottom: 12px;
}

.notice p {
  margin: 0;
}
</style>
