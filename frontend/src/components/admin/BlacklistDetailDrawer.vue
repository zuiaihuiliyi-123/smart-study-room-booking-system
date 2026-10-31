<script setup lang="ts">
/**
 * 黑名单记录详情抽屉（FR-044）。
 *
 * 展示记录的全部字段（用户、原因、来源、加入时间、期限、解除时间与解除原因、操作者），
 * 并在记录仍生效时提供**手动解除**入口（ST-043）：解除原因就地填写，必填，
 * 点按钮后只弹 `ElMessageBox.confirm` 二次确认，不叠第二个弹窗。
 *
 * 口径提示（BR-010 / ST-042）：若该账户存在管理员手动设置且仍生效的限制，系统不得自动解除；
 * 抽屉里直接写明，避免管理员误以为「等期限到了就会自动恢复」。
 */
import { computed, ref, watch } from 'vue'

import AuditNotice from '@/components/admin/AuditNotice.vue'
import StatusTag from '@/components/StatusTag.vue'
import type { BlacklistEntry } from '@/types'
import { operatorLabelOf, userLabelOf, type AdminDirectory } from '@/utils/adminData'
import { formatDateTime } from '@/utils/format'

const props = defineProps<{
  modelValue: boolean
  entry: BlacklistEntry | null
  directory: AdminDirectory | null
  scopeLabel: string
  submitting: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'release', reason: string): void
}>()

const reason = ref('')

watch(
  () => props.entry?.id,
  () => {
    reason.value = ''
  },
)

const state = computed(() => {
  const item = props.entry
  if (item === null) return '—'
  if (item.released_at !== null) return '已解除'
  if (item.expire_at === null) return '生效中'
  return new Date(item.expire_at).getTime() > Date.now() ? '生效中' : '已过期'
})

const canRelease = computed(() => props.entry !== null && props.entry.released_at === null)

/** 手动限制且未设期限 = 只能由管理员解除（ST-042 的例外） */
const manualNoExpire = computed(
  () => props.entry !== null && props.entry.mode === '手动' && props.entry.expire_at === null,
)

const title = computed(() =>
    props.entry === null ? '黑名单记录详情' : `黑名单记录详情 · #${props.entry.id}`,
)
</script>

<template>
  <el-drawer
    :model-value="props.modelValue"
    :title="title"
    size="600px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <AuditNotice
      :scope="props.scopeLabel"
      :reason-required="canRelease"
      :extra="'黑名单记录保留 1 年，不提供导出；解除必须填写原因并记录操作者。'"
    />

    <template v-if="props.entry">
      <div class="head">
        <strong>#{{ props.entry.id }}</strong>
        <StatusTag kind="blacklistState" :value="state" />
        <StatusTag kind="blacklist" :value="props.entry.mode" />
      </div>

      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="用户">
          {{ userLabelOf(props.directory, props.entry.user_id) }}
        </el-descriptions-item>
        <el-descriptions-item label="限制原因">{{ props.entry.reason }}</el-descriptions-item>
        <el-descriptions-item label="来源">
          {{ props.entry.mode === '自动' ? '自动（累计违约达 3 次触发）' : '手动（管理员加入）' }}
        </el-descriptions-item>
        <el-descriptions-item label="加入时间">
          {{ formatDateTime(props.entry.start_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="限制期限">
          <span v-if="props.entry.expire_at === null">
            不设期限
            <span class="ssr-text-muted">（只能由管理员手动解除）</span>
          </span>
          <span v-else>{{ formatDateTime(props.entry.expire_at) }}（期满自动解除）</span>
        </el-descriptions-item>
        <el-descriptions-item label="解除时间">
          {{ formatDateTime(props.entry.released_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="解除原因">
          <span v-if="props.entry.release_reason">{{ props.entry.release_reason }}</span>
          <span v-else-if="props.entry.released_reason">{{ props.entry.released_reason }}</span>
          <span v-else-if="props.entry.released_at !== null" class="ssr-text-muted">—</span>
          <span v-else class="ssr-text-muted">—</span>
        </el-descriptions-item>
        <el-descriptions-item label="操作者">
          {{ operatorLabelOf(props.directory, props.entry.operator_id) }}
          <span v-if="props.entry.released_by !== null" class="ssr-text-muted">
            · 解除人：{{ operatorLabelOf(props.directory, props.entry.released_by ?? null) }}
          </span>
        </el-descriptions-item>
      </el-descriptions>

      <el-alert v-if="manualNoExpire" class="notice" type="warning" :closable="false" show-icon title="该限制不会自动解除">
        <p>
          这是<strong>管理员手动</strong>加入且未设期限的限制：系统不得自动解除，必须由管理员在此手动解除，
          解除时须填写原因。
        </p>
      </el-alert>

      <el-form v-if="canRelease" label-width="96px" @submit.prevent>
        <el-form-item label="解除原因">
          <el-input
            v-model="reason"
            type="textarea"
            :rows="2"
            maxlength="255"
            show-word-limit
            placeholder="如：当事人提交情况说明，经核实后提前解除"
          />
        </el-form-item>
      </el-form>

      <div class="drawer-actions">
        <el-button @click="emit('update:modelValue', false)">关闭</el-button>
        <el-button
          v-if="canRelease"
          type="primary"
          :loading="props.submitting"
          :disabled="reason.trim() === ''"
          @click="emit('release', reason)"
        >
          手动解除限制
        </el-button>
      </div>
    </template>
  </el-drawer>
</template>

<style scoped>
.head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  margin-bottom: 10px;
  font-size: 15px;
}

.notice {
  margin-top: 12px;
}

.notice p {
  margin: 0;
  font-size: var(--ssr-font-note);
  line-height: 1.6;
}
</style>
