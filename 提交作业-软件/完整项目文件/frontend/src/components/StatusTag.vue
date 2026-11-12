<script setup lang="ts">
import { computed } from 'vue'

/** 状态域：只覆盖 AGENTS.md §4 定义的口径，不自行扩展 */
type StatusKind =
  | 'reservation'
  | 'seat'
  | 'complaint'
  | 'violation'
  | 'blacklist'
  | 'blacklistState'
  | 'account'
  | 'room'
type TagVariant = 'ok' | 'warn' | 'err' | 'info' | 'primary' | 'use' | 'fix' | 'off'

const props = withDefaults(
  defineProps<{
    kind: StatusKind
    value: string | null | undefined
    size?: 'large' | 'default' | 'small'
  }>(),
  { value: '', size: 'small' },
)

/**
 * 全站唯一的状态 → 标签映射表。
 * 色值不在此文件中出现，由 index.scss 的 .ssr-tag--* 使用 CSS 变量渲染。
 */
const STATUS_MAP: Record<StatusKind, Record<string, TagVariant>> = {
  // 预约状态（有效预约 = 待使用 / 使用中）
  reservation: {
    待使用: 'primary',
    使用中: 'use',
    已完成: 'ok',
    已取消: 'fix',
    已违约: 'err',
  },
  // 座位只有资源状态；"已预约""使用中"是时段派生结论，不写进座位状态
  seat: {
    可用: 'ok',
    维修中: 'fix',
    停用: 'off',
  },
  // 投诉状态
  complaint: {
    待处理: 'warn',
    处理中: 'primary',
    已处理: 'ok',
    已驳回: 'fix',
    已关闭: 'off',
  },
  // 违约类型
  violation: {
    自动违约: 'warn',
    手动违约: 'err',
  },
  // 黑名单来源
  blacklist: {
    自动: 'warn',
    手动: 'primary',
  },
  // 账户状态（FR-044 / ST-040～ST-046）：正常 / 受限 / 停用
  account: {
    正常: 'ok',
    受限: 'warn',
    停用: 'off',
  },
  // 黑名单记录的当前状态（SM-03 / ST-042）：生效中 / 已解除 / 已过期
  blacklistState: {
    生效中: 'err',
    已解除: 'ok',
    已过期: 'off',
  },
  // 自习室启用状态（FR-001）：以「停用」代替物理删除
  room: {
    启用: 'ok',
    停用: 'off',
  },
}

const variant = computed<TagVariant>(
  () => STATUS_MAP[props.kind][props.value ?? ''] ?? 'info',
)

const text = computed(() => props.value || '—')
</script>

<template>
  <el-tag
    class="ssr-tag"
    :class="`ssr-tag--${variant}`"
    :size="props.size"
    disable-transitions
  >
    {{ text }}
  </el-tag>
</template>
