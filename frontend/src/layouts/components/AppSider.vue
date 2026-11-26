<script setup lang="ts">
import { computed } from 'vue'

import { groupMenus, type MenuItem } from '@/layouts/menu'

const props = withDefaults(
  defineProps<{
    menus: MenuItem[]
    collapsed: boolean
    activePath: string
    /** 菜单项角标：path -> 数量；0 或未提供时不展示 */
    badges?: Record<string, number>
    /** 侧栏顶部用户卡（学生端）；不传则侧栏从顶部直接开始列菜单（管理端） */
    user?: { name: string; role: string }
  }>(),
  { badges: () => ({}) },
)

const groups = computed(() => groupMenus(props.menus))

/** 头像是首字占位，不引外部图片，暗色/浅色都不掉色 */
const userInitial = computed(() => props.user?.name?.slice(0, 1) || '同')
</script>

<template>
  <aside class="app-sider" :class="{ 'is-collapsed': props.collapsed }">
    <div v-if="props.user" class="app-sider__user">
      <span class="app-sider__avatar" aria-hidden="true">{{ userInitial }}</span>
      <span v-if="!props.collapsed" class="app-sider__user-meta">
        <strong>{{ props.user.name }}</strong>
        <small>{{ props.user.role }}</small>
      </span>
    </div>

    <el-menu
      router
      :default-active="props.activePath"
      :collapse="props.collapsed"
      :collapse-transition="false"
    >
      <template v-for="(group, index) in groups" :key="`${group.title}-${index}`">
        <li v-if="group.title && !props.collapsed" class="app-sider__group" role="presentation">
          {{ group.title }}
        </li>
        <li v-else-if="group.title" class="app-sider__divider" role="presentation" />
        <el-menu-item v-for="item in group.items" :key="item.path" :index="item.path" tabindex="0">
          <el-badge
            :value="props.badges[item.path] ?? 0"
            :max="99"
            :hidden="(props.badges[item.path] ?? 0) <= 0"
            class="app-sider__badge"
          >
            <el-icon v-if="item.icon"><component :is="item.icon" /></el-icon>
          </el-badge>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </template>
    </el-menu>
  </aside>
</template>

<style scoped>
.app-sider {
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  width: var(--ssr-aside-w);
  height: 100%;
  overflow: hidden;
  background: var(--ssr-surface);
  border-right: 1px solid var(--ssr-line);
}

.app-sider.is-collapsed {
  width: var(--ssr-aside-w-collapsed);
}

/* 用户卡：与 mock 一致——头像 + 姓名 + 角色，下面一条细线再进菜单 */
.app-sider__user {
  display: flex;
  flex: 0 0 auto;
  gap: 10px;
  align-items: center;
  padding: 18px 16px;
  border-bottom: 1px solid var(--ssr-line);
}

.app-sider.is-collapsed .app-sider__user {
  justify-content: center;
  padding: 14px 0;
  border-bottom: 0;
}

.app-sider__avatar {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  color: var(--ssr-primary-ink);
  font-size: 16px;
  font-weight: 600;
  background: var(--ssr-primary-light);
  border-radius: 50%;
}

.app-sider__user-meta {
  display: flex;
  flex-direction: column;
  min-width: 0;
  line-height: 1.35;
}

.app-sider__user-meta strong {
  overflow: hidden;
  color: var(--ssr-ink);
  font-size: var(--ssr-font-body);
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.app-sider__user-meta small {
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

/* 菜单自己滚动，用户卡固定 */
.app-sider :deep(.el-menu) {
  flex: 1 1 auto;
  min-height: 0;
  padding-top: 6px;
  overflow-y: auto;
  overflow-x: hidden;
}

.app-sider__group {
  padding: 14px 20px 6px;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  font-weight: 600;
  letter-spacing: 0.4px;
  list-style: none;
  user-select: none;
}

.app-sider__divider {
  height: 1px;
  margin: 8px 16px;
  background: var(--ssr-line);
  list-style: none;
}

.app-sider__badge {
  display: inline-flex;
  line-height: 1;
}

.app-sider__badge :deep(.el-badge__content) {
  height: 16px;
  padding: 0 5px;
  font-size: 10px;
  line-height: 14px;
}
</style>
