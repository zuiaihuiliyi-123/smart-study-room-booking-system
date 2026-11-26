<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import AppHeader from '@/layouts/components/AppHeader.vue'
import AppSider from '@/layouts/components/AppSider.vue'
import type { MenuItem } from '@/layouts/menu'

const props = withDefaults(
  defineProps<{
    menus: MenuItem[]
    /** 角色标签：品牌区副标题与面包屑根节点 */
    roleLabel: string
    /** 未读消息数；本轮由外层传入，壳层不自行取数 */
    unreadCount?: number
    /** 站内消息入口；管理端没有消息页面时关闭 */
    showMessages?: boolean
    /** 个人资料路由；不传则该下拉项禁用（如管理端暂无资料页） */
    profilePath?: string
    /** 侧栏菜单角标：path -> 数量（管理端待处理投诉等） */
    badges?: Record<string, number>
    /** 顶部横向主导航（学生端）；不传则顶栏只有品牌区，导航全在侧栏（管理端） */
    navItems?: MenuItem[]
    /** 顶部导航选中项；缺省按路由最长前缀在 navItems 里匹配 */
    navActivePath?: string
    /** 侧栏顶部用户卡（学生端） */
    siderUser?: { name: string; role: string }
    /** 是否显示面包屑；学生端改为顶栏导航后不再需要 */
    showCrumb?: boolean
    /** 学生端用户区：头像 + 姓名 + 退出文字按钮 */
    plainUser?: boolean
    /** 是否显示侧栏；学生端只有「个人中心」下的页面显示侧栏，首页与选座页让正文占满 */
    showSider?: boolean
    /**
     * 正文是否铺满可用宽度。学生端开启：去掉 .page 的 1440px 上限，
     * 否则宽屏（1920 等）右侧会留出一大块空白。
     */
    fillWidth?: boolean
  }>(),
  {
    unreadCount: 0,
    showMessages: true,
    profilePath: '',
    badges: () => ({}),
    navItems: () => [],
    navActivePath: '',
    showCrumb: true,
    plainUser: false,
    showSider: true,
    fillWidth: false,
  },
)

const emit = defineEmits<{ (e: 'messages'): void }>()

const route = useRoute()

const collapsed = ref(false)
const narrow = ref(false)

let media: MediaQueryList | null = null

function onMediaChange(event: MediaQueryListEvent | MediaQueryList) {
  narrow.value = event.matches
  collapsed.value = event.matches
}

onMounted(() => {
  media = window.matchMedia('(max-width: 1024px)')
  onMediaChange(media)
  media.addEventListener('change', onMediaChange)
})

onBeforeUnmount(() => {
  media?.removeEventListener('change', onMediaChange)
})

/** 选中态：取与当前路由最长前缀匹配的菜单项 */
const activePath = computed(() => {
  const current = route.path
  const hit = props.menus
    .filter((item) => current === item.path || current.startsWith(`${item.path}/`))
    .sort((a, b) => b.path.length - a.path.length)[0]
  return hit ? hit.path : current
})

/** 顶部导航选中项：显式传入优先（个人中心把多个二级页归到一个模块） */
const navActive = computed(() => {
  if (props.navActivePath) return props.navActivePath
  const current = route.path
  const hit = props.navItems
    .filter((item) => current === item.path || current.startsWith(`${item.path}/`))
    .sort((a, b) => b.path.length - a.path.length)[0]
  return hit ? hit.path : current
})

/** 面包屑：角色标签 → 各层路由 meta.title */
const crumbs = computed(() =>
  route.matched
    .filter((record) => Boolean(record.meta.title))
    .map((record) => ({ path: record.path, title: String(record.meta.title) })),
)
</script>

<template>
  <div class="app-shell">
    <AppHeader
      :role-label="props.roleLabel"
      :collapsed="collapsed"
      :narrow="narrow && props.showSider"
      :unread-count="props.unreadCount"
      :show-messages="props.showMessages"
      :profile-path="props.profilePath"
      :nav-items="props.navItems"
      :nav-active-path="navActive"
      :plain-user="props.plainUser"
      @messages="emit('messages')"
      @toggle="collapsed = !collapsed"
    />

    <div class="app-body">
      <AppSider
        v-if="props.showSider"
        :menus="props.menus"
        :collapsed="collapsed"
        :active-path="activePath"
        :badges="props.badges"
        :user="props.siderUser"
      />

      <div class="app-content">
        <nav v-if="props.showCrumb" class="app-crumb" aria-label="面包屑导航">
          <ol class="app-crumb__list">
            <li class="app-crumb__root">{{ props.roleLabel }}</li>
            <li v-for="(crumb, index) in crumbs" :key="crumb.path" class="app-crumb__item">
              <span class="app-crumb__sep" aria-hidden="true">/</span>
              <router-link
                v-if="index < crumbs.length - 1"
                class="app-crumb__link"
                :to="crumb.path"
              >
                {{ crumb.title }}
              </router-link>
              <span v-else class="app-crumb__current" aria-current="page">{{ crumb.title }}</span>
            </li>
          </ol>
        </nav>

        <main class="app-main" :class="{ 'app-main--fill': props.fillWidth }">
          <router-view />
        </main>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app-shell {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--ssr-bg);
}

.app-body {
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
}

.app-content {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  min-width: 0;
}

.app-crumb {
  flex: 0 0 auto;
  height: var(--ssr-crumb-h);
  background: var(--ssr-surface);
  border-bottom: 1px solid var(--ssr-line);
}

.app-crumb__list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  height: 100%;
  max-width: var(--ssr-main-max);
  padding: 0 var(--ssr-gutter);
  margin: 0;
  overflow: hidden;
  list-style: none;
}

.app-crumb__root,
.app-crumb__item {
  display: inline-flex;
  gap: 6px;
  align-items: center;
  font-size: var(--ssr-font-note);
}

.app-crumb__root {
  color: var(--ssr-muted-ink);
}

.app-crumb__sep {
  color: var(--ssr-muted);
}

.app-crumb__link {
  color: var(--ssr-primary-ink);
  text-decoration: none;
}

.app-crumb__link:hover {
  text-decoration: underline;
}

.app-crumb__current {
  color: var(--ssr-ink);
  font-weight: 600;
}

.app-main {
  flex: 1 1 auto;
  min-height: 0;
  overflow: auto;
}
</style>
