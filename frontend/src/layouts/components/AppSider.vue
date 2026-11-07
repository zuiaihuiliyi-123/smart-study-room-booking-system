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
  }>(),
  { badges: () => ({}) },
)

const groups = computed(() => groupMenus(props.menus))
</script>

<template>
  <aside class="app-sider" :class="{ 'is-collapsed': props.collapsed }">
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
        <el-menu-item
          v-for="item in group.items"
          :key="item.path"
          :index="item.path"
          tabindex="0"
        >
          <el-badge
            :value="props.badges[item.path] ?? 0"
            :max="99"
            :hidden="(props.badges[item.path] ?? 0) <= 0"
            class="app-sider__badge"
          >
            <el-icon><component :is="item.icon" /></el-icon>
          </el-badge>
          <template #title>{{ item.title }}</template>
        </el-menu-item>
      </template>
    </el-menu>
  </aside>
</template>

<style scoped>
.app-sider {
  flex: 0 0 auto;
  width: var(--ssr-aside-w);
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--ssr-surface);
  border-right: 1px solid var(--ssr-line);
}

.app-sider.is-collapsed {
  width: var(--ssr-aside-w-collapsed);
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
