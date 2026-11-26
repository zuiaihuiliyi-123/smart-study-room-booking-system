<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowDown, Bell, Expand, Fold, Moon, Sunny } from '@element-plus/icons-vue'

import type { MenuItem } from '@/layouts/menu'
import { useAuthStore } from '@/stores/auth'
import { useTheme } from '@/utils/useTheme'

const props = withDefaults(
  defineProps<{
    /** 角色标签：品牌区副标题，兼作用户角色兜底 */
    roleLabel: string
    collapsed: boolean
    /** ≤1024px 时出现折叠按钮 */
    narrow: boolean
    unreadCount?: number
    /** 站内消息入口；管理端没有消息页面时关闭，避免出现点了没反应的按钮 */
    showMessages?: boolean
    /** 个人资料路由；不传则该下拉项禁用 */
    profilePath?: string
    /** 顶部横向主导航（学生端）；不传则顶栏只有品牌区（管理端沿用侧栏导航） */
    navItems?: MenuItem[]
    /** 顶部导航选中项：与 router 路径不同源（个人中心的二级页都算「个人中心」） */
    navActivePath?: string
    /** 学生端顶栏：头像 + 姓名 + 「退出」文字按钮，替代管理端的下拉菜单 */
    plainUser?: boolean
  }>(),
  {
    unreadCount: 0,
    showMessages: true,
    profilePath: '',
    navItems: () => [],
    navActivePath: '',
    plainUser: false,
  },
)

const emit = defineEmits<{
  (e: 'messages'): void
  (e: 'toggle'): void
}>()

const router = useRouter()
const auth = useAuthStore()
const { isDark, toggleTheme } = useTheme()

const hasNav = computed(() => props.navItems.length > 0)

/** 品牌区与侧栏同宽对齐；有顶部导航时改成自然宽度，把空间让给导航 */
const brandStyle = computed(() => {
  if (hasNav.value) return undefined
  return props.collapsed
    ? { width: 'var(--ssr-aside-w-collapsed)' }
    : { width: 'var(--ssr-aside-w)' }
})

/** 头像占位：取姓名首字 */
const userInitial = computed(() => auth.user?.name?.slice(0, 1) || '同')

function onCommand(command: string) {
  if (command === 'logout') {
    // 本地凭据在 logout() 内同步清除，可立即跳转；服务端撤销在后台完成
    void auth.logout()
    void router.push('/login')
    return
  }
  if (command === 'profile' && props.profilePath) {
    void router.push(props.profilePath)
  }
}
</script>

<template>
  <header class="app-header" :class="{ 'app-header--nav': hasNav }">
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
      <span v-if="!props.collapsed || hasNav" class="app-header__brand-text">
        <strong>智慧自习室</strong>
        <small>{{ props.roleLabel }}</small>
      </span>
    </div>

    <nav v-if="hasNav" class="app-header__nav" aria-label="主导航">
      <router-link
        v-for="item in props.navItems"
        :key="item.path"
        :to="item.path"
        class="app-header__nav-item"
        :class="{ 'is-active': item.path === props.navActivePath }"
        :aria-current="item.path === props.navActivePath ? 'page' : undefined"
      >
        {{ item.title }}
      </router-link>
    </nav>

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

      <button
        class="app-icon-btn"
        type="button"
        :aria-label="isDark ? '切换到浅色主题' : '切换到暗色主题'"
        :title="isDark ? '切换到浅色主题' : '切换到暗色主题'"
        @click="toggleTheme"
      >
        <Transition name="ssr-theme-icon" mode="out-in">
          <el-icon :key="isDark ? 'sunny' : 'moon'">
            <component :is="isDark ? Sunny : Moon" />
          </el-icon>
        </Transition>
      </button>

      <el-badge
        v-if="props.showMessages"
        class="app-header__badge"
        :value="props.unreadCount"
        :max="99"
        :hidden="props.unreadCount === 0"
      >
        <button class="app-icon-btn" type="button" aria-label="站内消息" @click="emit('messages')">
          <el-icon><Bell /></el-icon>
        </button>
      </el-badge>

      <template v-if="props.plainUser">
        <button
          class="app-user app-user--plain"
          type="button"
          :title="props.profilePath ? '个人资料' : undefined"
          @click="onCommand('profile')"
        >
          <span class="app-user__avatar" aria-hidden="true">{{ userInitial }}</span>
          <span class="app-user__name">{{ auth.user?.name ?? '未登录' }}</span>
        </button>
        <button class="app-logout" type="button" @click="onCommand('logout')">退出</button>
      </template>

      <el-dropdown v-else trigger="click" @command="onCommand">
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
  color: var(--ssr-ink);
  /* Linear：顶栏与侧栏同为一档暗色 chrome，主色只留给操作与选中 */
  background: var(--ssr-surface);
  border-bottom: 1px solid var(--ssr-line);
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
  font-size: 17px;
  font-weight: 600;
  white-space: nowrap;
}

.app-header__brand-text small {
  font-size: var(--ssr-font-note);
  opacity: 0.85;
}

/* 有顶部导航时：品牌自然宽度 + 左内距对齐正文，横向导航从品牌右侧开始 */
.app-header--nav .app-header__brand {
  padding-left: var(--ssr-gutter);
}

.app-header__nav {
  display: flex;
  flex: 1 1 auto;
  align-items: stretch;
  min-width: 0;
  height: 100%;
  margin-left: 8px;
  overflow-x: auto;
  scrollbar-width: none;
}

.app-header__nav::-webkit-scrollbar {
  display: none;
}

.app-header__nav-item {
  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  padding: 0 16px;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-body);
  text-decoration: none;
  white-space: nowrap;
}

/* 宽屏把导航放在品牌与操作区之间居中（与 mock 一致）；窄屏靠左排，避免溢出被裁掉开头 */
@media (min-width: 1100px) {
  .app-header__nav {
    justify-content: center;
  }
}

.app-header__nav-item:hover {
  color: var(--ssr-ink);
}

/* 选中态：加粗主色 + 3px 下划线（与侧栏 3px 竖条同一套选中语言） */
.app-header__nav-item.is-active {
  color: var(--ssr-primary-ink);
  font-weight: 600;
}

.app-header__nav-item.is-active::after {
  position: absolute;
  right: 16px;
  bottom: 0;
  left: 16px;
  height: 3px;
  content: '';
  background: var(--ssr-primary);
  border-radius: 3px 3px 0 0;
}

/* 窄屏（<=720px）：顶栏折成两行——品牌与操作区一行、导航独占一行，保证三个入口都点得到 */
@media (max-width: 720px) {
  .app-header--nav {
    flex-wrap: wrap;
    height: auto;
    min-height: var(--ssr-header-h);
  }

  .app-header--nav .app-header__brand,
  .app-header--nav .app-header__actions {
    height: 56px;
  }

  .app-header--nav .app-header__brand {
    gap: 6px;
    padding-left: 12px;
  }

  .app-header__brand-text small {
    display: none;
  }

  .app-header__nav {
    order: 3;
    flex: 1 0 100%;
    height: 44px;
    margin-left: 0;
    border-top: 1px solid var(--ssr-line);
  }

  .app-header__nav-item {
    flex: 1 0 auto;
    justify-content: center;
    padding: 0 10px;
    font-size: var(--ssr-font-note);
  }
}

/* 手机竖屏：品牌只留图标，让品牌区与操作区挤在同一行，顶栏只折成两行 */
@media (max-width: 480px) {
  .app-header--nav .app-header__brand-text {
    display: none;
  }
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
  width: 36px;
  height: 36px;
  font-size: 18px;
  color: var(--ssr-ink);
  background: transparent;
  border: 0;
  border-radius: var(--ssr-radius-sm);
  cursor: pointer;
}

.app-icon-btn:hover {
  background: var(--ssr-primary-light);
}

/* 主题开关的图标：Moon ↔ Sunny 做一次淡出淡入（各 0.14s，合计与整页过渡同节奏） */
.ssr-theme-icon-enter-active,
.ssr-theme-icon-leave-active {
  transition: opacity 0.14s ease;
}

.ssr-theme-icon-enter-from,
.ssr-theme-icon-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .ssr-theme-icon-enter-active,
  .ssr-theme-icon-leave-active {
    transition: none;
  }
}

.app-header__badge {
  display: inline-flex;
}

.app-user {
  display: inline-flex;
  gap: 8px;
  align-items: center;
  height: 38px;
  padding: 0 10px;
  color: var(--ssr-ink);
  background: transparent;
  border: 0;
  border-radius: var(--ssr-radius-sm);
  cursor: pointer;
}

.app-user:hover {
  background: var(--ssr-primary-light);
}

.app-user__name {
  font-size: var(--ssr-font-body);
  font-weight: 600;
}

.app-user__role {
  padding: 1px 7px;
  font-size: var(--ssr-font-note);
  /* 浅底 + 深字：浅色 #3f4899/#eeeffb 约 5.6:1，暗色 #a9b2f7/白 6% 约 8:1，两套主题都过 AA */
  color: var(--ssr-primary-ink);
  background: var(--ssr-primary-light);
  border-radius: var(--ssr-radius-sm);
}

.app-user__caret {
  font-size: 12px;
}

/* 学生端顶栏：头像占位 + 姓名，点进个人资料 */
.app-user--plain {
  gap: 8px;
  padding: 0 8px;
}

.app-user__avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  color: var(--ssr-primary-ink);
  font-size: 14px;
  font-weight: 600;
  background: var(--ssr-primary-light);
  border-radius: 50%;
}

.app-logout {
  height: 32px;
  padding: 0 8px;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  background: transparent;
  border: 0;
  border-radius: var(--ssr-radius-sm);
  cursor: pointer;
}

.app-logout:hover {
  color: var(--ssr-ink);
  background: var(--ssr-primary-light);
}
</style>
