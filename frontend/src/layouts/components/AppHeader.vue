<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowDown, Bell, Expand, Fold } from '@element-plus/icons-vue'

import { useAuthStore } from '@/stores/auth'

const props = withDefaults(
  defineProps<{
    /** 角色标签：品牌区副标题，兼作用户角色兜底 */
    roleLabel: string
    collapsed: boolean
    /** ≤1024px 时出现折叠按钮 */
    narrow: boolean
    unreadCount?: number
    /** 个人资料路由；不传则该下拉项禁用 */
    profilePath?: string
  }>(),
  { unreadCount: 0, profilePath: '' },
)

const emit = defineEmits<{
  (e: 'messages'): void
  (e: 'toggle'): void
}>()

const router = useRouter()
const auth = useAuthStore()

/** 品牌区与侧栏同宽对齐 */
const brandStyle = computed(() =>
    props.collapsed ? { width: 'var(--ssr-aside-w-collapsed)' } : { width: 'var(--ssr-aside-w)' },
)

function onCommand(command: string) {
  if (command === 'logout') {
    auth.logout()
    void router.push('/login')
    return
  }
  if (command === 'profile' && props.profilePath) {
    void router.push(props.profilePath)
  }
}
</script>

<template>
  <header class="app-header">
    <div class="app-header__brand" :style="brandStyle">
      <svg class="app-header__mark" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
        <rect
          x="1"
          y="1"
          width="30"
          height="30"
          rx="8"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        />
        <rect x="7" y="9" width="18" height="3" rx="1.5" fill="currentColor" />
        <rect x="8" y="15" width="5" height="8" rx="1.5" fill="currentColor" />
        <rect x="19" y="15" width="5" height="8" rx="1.5" fill="currentColor" />
      </svg>
      <span v-if="!props.collapsed" class="app-header__brand-text">
        <strong>智慧自习室</strong>
        <small>{{ props.roleLabel }}</small>
      </span>
    </div>

    <div class="app-header__actions">
      <button
        v-if="props.narrow"
        class="app-icon-btn"
        type="button"
        :aria-label="props.collapsed ? '展开菜单' : '收起菜单'"
        :aria-expanded="!props.collapsed"
        @click="emit('toggle')"
      >
        <el-icon><component :is="props.collapsed ? Expand : Fold" /></el-icon>
      </button>

      <el-badge
        class="app-header__badge"
        :value="props.unreadCount"
        :max="99"
        :hidden="props.unreadCount === 0"
      >
        <button class="app-icon-btn" type="button" aria-label="站内消息" @click="emit('messages')">
          <el-icon><Bell /></el-icon>
        </button>
      </el-badge>

      <el-dropdown trigger="click" @command="onCommand">
        <button class="app-user" type="button" aria-haspopup="menu">
          <span class="app-user__name">{{ auth.user?.name ?? '未登录' }}</span>
          <span class="app-user__role">{{ auth.user?.role ?? props.roleLabel }}</span>
          <el-icon class="app-user__caret"><ArrowDown /></el-icon>
        </button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="profile" :disabled="!props.profilePath">
              个人资料
            </el-dropdown-item>
            <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  height: var(--ssr-header-h);
  color: var(--ssr-on-primary);
  background: var(--ssr-primary);
}

.app-header__brand {
  display: flex;
  flex: 0 0 auto;
  gap: 10px;
  align-items: center;
  height: 100%;
  padding: 0 12px 0 16px;
}

.app-header__mark {
  flex: 0 0 auto;
  width: 28px;
  height: 28px;
}

.app-header__brand-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.25;
}

.app-header__brand-text strong {
  font-size: 15px;
  font-weight: 600;
  white-space: nowrap;
}

.app-header__brand-text small {
  font-size: var(--ssr-font-note);
  opacity: 0.85;
}

.app-header__actions {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-left: auto;
  padding: 0 16px;
}

.app-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  color: var(--ssr-on-primary);
  background: transparent;
  border: 0;
  border-radius: var(--ssr-radius-sm);
  cursor: pointer;
}

.app-icon-btn:hover {
  background: rgb(255 255 255 / 16%);
}

.app-header__badge {
  display: inline-flex;
}

.app-user {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  height: 34px;
  padding: 0 10px;
  color: var(--ssr-on-primary);
  background: transparent;
  border: 0;
  border-radius: var(--ssr-radius-sm);
  cursor: pointer;
}

.app-user:hover {
  background: rgb(255 255 255 / 16%);
}

.app-user__name {
  font-size: var(--ssr-font-body);
  font-weight: 600;
}

.app-user__role {
  padding: 1px 7px;
  font-size: var(--ssr-font-note);
  /* 18% 白底 + 白字在 #2B5F9E 上只有 4.32:1，改用深蓝实底（8.74:1） */
  background: var(--ssr-primary-deep);
  border-radius: 10px;
}

.app-user__caret {
  font-size: 12px;
}
</style>
