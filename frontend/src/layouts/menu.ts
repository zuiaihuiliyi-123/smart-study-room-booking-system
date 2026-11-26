import type { Component } from 'vue'
import {
  Bell,
  ChatDotRound,
  CircleClose,
  DataLine,
  Document,
  Grid,
  OfficeBuilding,
  Star,
  Tickets,
  User,
  UserFilled,
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
  /** 侧栏菜单项必填；顶部横向导航只排文字，不需要图标 */
  icon?: Component
  group?: string
}

export interface MenuGroup {
  title: string
  items: MenuItem[]
}

/**
 * 学生端顶部主导航（一级）：只放模块入口。
 * 「个人中心」是分组入口，具体页面在下方 studentMenus 的侧栏里二级展开。
 */
export const studentNavMenus: MenuItem[] = [
  { path: '/student/home', title: '首页' },
  { path: '/student/booking', title: '预约座位' },
  { path: '/student/profile', title: '个人中心' },
]

/**
 * 学生端侧栏菜单（个人中心二级导航）。
 * 与顶部导航分工：顶部是模块，侧栏是「我的」相关页面。
 * 本期不含 AI 助手、会员卡、购买记录、信用与申诉（AGENTS.md §5.8 排除项），
 * 违约记录只做查看，不提供申诉入口。
 */
export const studentMenus: MenuItem[] = [
  { path: '/student/reservations', title: '我的预约', icon: Tickets },
  { path: '/student/violations', title: '我的违约', icon: Warning },
  { path: '/student/complaints', title: '我的投诉', icon: ChatDotRound },
  { path: '/student/messages', title: '站内消息', icon: Bell },
  { path: '/student/profile', title: '个人资料', icon: User },
]

/** 管理端菜单：仅自习室管理员（R-02）可见。
 * 系统管理员（R-04）本版无业务操作权限（BR-018 §4.1.1 定稿矩阵），
 * AdminLayout 对其传空菜单并由 /admin/notice 承接。 */
export const adminMenus: MenuItem[] = [
  { path: '/admin/dashboard', title: '数据看板', icon: DataLine, group: '数据概览' },
  { path: '/admin/rooms', title: '自习室管理', icon: OfficeBuilding, group: '资源管理' },
  { path: '/admin/seats', title: '座位管理', icon: Grid, group: '资源管理' },
  { path: '/admin/reservations', title: '预约管理', icon: Tickets, group: '业务管理' },
  { path: '/admin/violations', title: '违约管理', icon: Warning, group: '业务管理' },
  { path: '/admin/complaints', title: '投诉处理', icon: ChatDotRound, group: '业务管理' },
  { path: '/admin/reviews', title: '评价管理', icon: Star, group: '业务管理' },
  { path: '/admin/users', title: '用户管理', icon: User, group: '用户与风控' },
  { path: '/admin/blacklist', title: '黑名单管理', icon: CircleClose, group: '用户与风控' },
  { path: '/admin/audit', title: '审计日志', icon: Document, group: '用户与风控' },
  { path: '/admin/profile', title: '个人资料', icon: UserFilled, group: '账户' },
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
