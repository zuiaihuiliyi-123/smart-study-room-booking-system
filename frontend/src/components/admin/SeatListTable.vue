<script setup lang="ts">
/**
 * 管理端座位列表视图（FR-003 / FR-031）。
 *
 * 与网格视图共用同一份选择（`selectedIds`），切换视图时选择不会丢失：
 * 本组件在挂载与 `selectedIds` 变化时把选择回填给表格，表格勾选变化时再向上同步。
 * 两个维度分列呈现：**资源状态**（seat.status）与**该时段占用**（occupancy）。
 */
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import type { TableInstance } from 'element-plus'

import StatusTag from '@/components/StatusTag.vue'
import type { SeatOccupancy } from '@/types'
import { areaLabelOf, seatIdLabel, userLabelOf, type AdminDirectory } from '@/utils/adminData'

const props = defineProps<{
  items: SeatOccupancy[]
  allSeats: SeatOccupancy[]
  directory: AdminDirectory | null
  selectedIds: number[]
}>()

const emit = defineEmits<{
  (e: 'update:selectedIds', value: number[]): void
  (e: 'open', row: SeatOccupancy): void
}>()

const tableRef = ref<TableInstance>()

function tableIds(): number[] {
  const table = tableRef.value
  if (!table) return []
  const rows = table.getSelectionRows() as SeatOccupancy[] | undefined
  return (rows ?? []).map((row) => row.seat.id)
}

/** 只补齐差异，避免与 `selection-change` 形成循环 */
async function syncSelection(): Promise<void> {
  await nextTick()
  const table = tableRef.value
  if (!table) return
  const current = tableIds()
  const missing = props.selectedIds.filter((id) => !current.includes(id))
  const extra = current.filter((id) => !props.selectedIds.includes(id))
  if (missing.length === 0 && extra.length === 0) return
  table.clearSelection()
  for (const row of props.items) {
    if (props.selectedIds.includes(row.seat.id)) table.toggleRowSelection(row, true)
  }
}

function onSelectionChange(rows: SeatOccupancy[]): void {
  const ids = rows.map((row) => row.seat.id)
  const same =
    ids.length === props.selectedIds.length && ids.every((id) => props.selectedIds.includes(id))
  if (!same) emit('update:selectedIds', ids)
}

watch(() => props.selectedIds, syncSelection, { deep: true })
watch(() => props.items, syncSelection)
onMounted(syncSelection)

const seatsOfRoom = computed(() => props.allSeats.map((item) => item.seat))
</script>

<template>
  <div class="table-wrap">
    <el-table
      ref="tableRef"
      :data="props.items"
      size="small"
      border
      row-key="seat.id"
      style="min-width: 1020px"
      @selection-change="onSelectionChange"
    >
      <el-table-column type="selection" width="44" reserve-selection />

      <el-table-column label="座位号" width="96">
        <template #default="{ row }">
          <strong>{{ row.seat.seat_no }}</strong>
        </template>
      </el-table-column>

      <el-table-column label="自习室 · 分区" min-width="190">
        <template #default="{ row }">
          {{ seatIdLabel(props.directory, row.seat.id) }}
          <div class="ssr-text-muted">
            分区：{{ areaLabelOf(props.directory, row.seat.area_id, seatsOfRoom) }}
          </div>
        </template>
      </el-table-column>

      <el-table-column label="座位类型" width="120">
        <template #default="{ row }">{{ row.seat.seat_type }}</template>
      </el-table-column>

      <el-table-column label="插座" width="80">
        <template #default="{ row }">{{ row.seat.has_power ? '有' : '无' }}</template>
      </el-table-column>

      <el-table-column label="资源状态" width="110">
        <template #default="{ row }">
          <StatusTag kind="seat" :value="row.seat.status" />
        </template>
      </el-table-column>

      <el-table-column label="该时段占用" min-width="190">
        <template #default="{ row }">
          <el-tag v-if="row.seat.status !== '可用'" class="ssr-tag ssr-tag--off" disable-transitions>
            未判定
          </el-tag>
          <el-tag
            v-else
            class="ssr-tag"
            :class="row.occupied ? 'ssr-tag--use' : 'ssr-tag--ok'"
            disable-transitions
          >
            {{ row.occupied ? '已被预约' : '可约' }}
          </el-tag>
          <div v-if="row.reservation" class="ssr-text-muted">
            预约人：{{ userLabelOf(props.directory, row.reservation.user_id) }}（#{{ row.reservation.id }}）
          </div>
          <div v-else-if="row.seat.status !== '可用'" class="ssr-text-muted">
            资源状态不可用，接口不返回占用
          </div>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="110" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="emit('open', row)">调整状态</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>
