<script setup lang="ts">
/**
 * 用户详情抽屉（FR-040）。
 *
 * **只读**：不提供任何编辑入口。依据 BR-018 / Q-030 的本版裁定，管理员不可编辑姓名、学号等
 * 身份信息与口令，也不得代改联系方式（联系方式是用户唯一可自行修改的字段）。
 * 账户状态的变更不在此处发生——一律走 FR-044 的黑名单流程，因此抽屉底部提供跳转入口。
 *
 * NFR-006：联系方式按形态掩码展示（手机号 / 邮箱），并标注「已掩码」以免被误认为原值。
 */
import StatusTag from '@/components/StatusTag.vue'
import type { CurrentUser } from '@/types'
import { formatDateTime } from '@/utils/format'
import { contactKindLabel, maskContact } from '@/utils/mask'

const props = defineProps<{
  modelValue: boolean
  user: CurrentUser | null
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: boolean): void
  (e: 'open-blacklist', userId: number): void
}>()
</script>

<template>
  <el-drawer
    :model-value="props.modelValue"
    :title="props.user === null ? '用户详情' : `用户详情 · ${props.user.name}`"
    size="560px"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <template v-if="props.user">
      <div class="head">
        <strong>{{ props.user.name }}</strong>
        <StatusTag kind="account" :value="props.user.account_status" />
      </div>

      <el-descriptions :column="1" border size="small">
        <el-descriptions-item label="用户编号">#{{ props.user.id }}</el-descriptions-item>
        <el-descriptions-item label="姓名">{{ props.user.name }}</el-descriptions-item>
        <el-descriptions-item label="学号 / 工号">{{ props.user.student_no }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ props.user.role }}</el-descriptions-item>
        <el-descriptions-item label="账户状态">{{ props.user.account_status }}</el-descriptions-item>
        <el-descriptions-item label="累计违约次数">
          {{ props.user.violation_count }} / 3
          <span class="ssr-text-muted">（达到 3 次由系统自动限制 7 天）</span>
        </el-descriptions-item>
        <el-descriptions-item label="联系方式">
          {{ maskContact(props.user.contact) }}
          <span class="ssr-text-muted">
            （{{ contactKindLabel(props.user.contact) }}，已做掩码处理；用户可在个人资料中自行修改）
          </span>
        </el-descriptions-item>
        <el-descriptions-item label="预计解除时间">
          <span v-if="props.user.account_status !== '受限'" class="ssr-text-muted">—</span>
          <span v-else-if="props.user.restrict_until">
            {{ formatDateTime(props.user.restrict_until) }}
          </span>
          <span v-else class="ssr-text-muted">管理员手动限制，无自动解除时间</span>
        </el-descriptions-item>
      </el-descriptions>

      <el-alert class="notice" type="info" :closable="false" show-icon title="只读说明">
        <p>
          本版裁定：管理员<strong>仅可查询</strong>用户信息，<strong>不可编辑</strong>姓名、学号、院系等身份信息与口令，
          也不可代改联系方式。
        </p>
        <p>
          账户状态（正常 / 受限 / 停用）不经由本页修改：下方按钮跳转到「黑名单管理」，在那里加入或解除限制。
        </p>
      </el-alert>

      <div class="drawer-actions">
        <el-button @click="emit('update:modelValue', false)">关闭</el-button>
        <el-button type="primary" @click="emit('open-blacklist', props.user.id)">
          跳转到黑名单管理
        </el-button>
      </div>
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
