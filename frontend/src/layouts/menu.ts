import type { Component } from 'vue'
import {
  Bell,
  Calendar,
  ChatDotRound,
  CircleClose,
  DataLine,
  Grid,
  HomeFilled,
  OfficeBuilding,
  Tickets,
  User,
  Warning,
} from '@element-plus/icons-vue'

/**
 * 侧栏菜单项。
 * - path：与 router 中的路由路径一一对应（el-menu 的 index，同时也用于选中态匹配）
 * - icon：@element-plus/icons-vue 的组件
 * - group：可选分组标题；连续同 group 的项会渲染在同一个分组标题下，缺省则不分组
 */
export interface MenuItem {
  path: string
  title: string
  icon: Component
  group?: string
}

export interface MenuGroup {
  title: string
  items: MenuItem[]
}

/** 学生端菜单（含教师用户，路由守卫同组放行） */
export const studentMenus: MenuItem[] = [
  { path: '/student/home', title: '首页', icon: HomeFilled, group: '学习服务' },
  { path: '/student/booking', title: '预约座位', icon: Calendar, group: '学习服务' },
  { path: '/student/reservations', title: '我的预约', icon: Tickets, group: '学习服务' },
  { path: '/student/violations', title: '我的违约', icon: Warning, group: '我的记录' },
  { path: '/student/complaints', title: '我的投诉', icon: ChatDotRound, group: '我的记录' },
  { path: '/student/messages', title: '站内消息', icon: Bell, group: '我的记录' },
  { path: '/student/profile', title: '个人资料', icon: User, group: '账户' },
]

/** 管理端菜单（自习室管理员 / 系统管理员共用） */
export const adminMenus: MenuItem[] = [
  { path: '/admin/dashboard', title: '数据看板', icon: DataLine, group: '数据概览' },
  { path: '/admin/rooms', title: '自习室管理', icon: OfficeBuilding, group: '资源管理' },
  { path: '/admin/seats', title: '座位管理', icon: Grid, group: '资源管理' },
  { path: '/admin/reservations', title: '预约管理', icon: Tickets, group: '业务管理' },
  { path: '/admin/violations', title: '违约管理', icon: Warning, group: '业务管理' },
  { path: '/admin/complaints', title: '投诉处理', icon: ChatDotRound, group: '业务管理' },
  { path: '/admin/users', title: '用户管理', icon: User, group: '用户与风控' },
  { path: '/admin/blacklist', title: '黑名单管理', icon: CircleClose, group: '用户与风控' },
]

/**
 * 把带 group 的平铺数组折叠成分组结构。
 * 未标注 group 的项归入空标题分组，渲染时不显示分组标题。
 */
export function groupMenus(items: MenuItem[]): MenuGroup[] {
  const groups: MenuGroup[] = []
  for (const item of items) {
    const title = item.group ?? ''
    const last = groups[groups.length - 1]
    if (last && last.title === title) {
      last.items.push(item)
    } else {
      groups.push({ title, items: [item] })
    }
  }
  return groups
}
