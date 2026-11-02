import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import type { Role } from '@/types'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/student',
    component: () => import('@/layouts/StudentLayout.vue'),
    meta: { roles: ['学生用户', '教师用户'] },
    children: [
      { path: '', redirect: '/student/home' },
      {
        path: 'home',
        name: 'student-home',
        component: () => import('@/views/student/HomeView.vue'),
        meta: { title: '首页' },
      },
      {
        path: 'booking',
        name: 'student-booking',
        component: () => import('@/views/student/SeatBookingView.vue'),
        meta: { title: '预约座位' },
      },
      {
        path: 'reservations',
        name: 'student-reservations',
        component: () => import('@/views/student/MyReservationsView.vue'),
        meta: { title: '我的预约' },
      },
      {
        path: 'violations',
        name: 'student-violations',
        component: () => import('@/views/student/MyViolationsView.vue'),
        meta: { title: '我的违约' },
      },
      {
        path: 'complaints',
        name: 'student-complaints',
        component: () => import('@/views/student/StudentComplaintsView.vue'),
        meta: { title: '我的投诉' },
      },
      {
        path: 'messages',
        name: 'student-messages',
        component: () => import('@/views/student/MessagesView.vue'),
        meta: { title: '站内消息' },
      },
      {
        path: 'profile',
        name: 'student-profile',
        component: () => import('@/views/student/ProfileView.vue'),
        meta: { title: '个人资料' },
      },
    ],
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { roles: ['自习室管理员', '系统管理员'] },
    children: [
      // 系统管理员（R-04）本版无业务操作权限（BR-018 §4.1.1 定稿矩阵），
      // 仅未来"全局参数配置"归其所有（本期未实现）。业务页 roles 只含业务管理员，
      // 系统管理员由根 redirect 导向下方 notice 页，避免进入业务页被 403 刷屏。
      {
        path: '',
        redirect: () => {
          const auth = useAuthStore()
          return auth.isSystemAdmin ? '/admin/notice' : '/admin/dashboard'
        },
      },
      {
        path: 'notice',
        name: 'admin-notice',
        component: () => import('@/views/admin/SystemAdminNoticeView.vue'),
        meta: { title: '系统管理员', roles: ['自习室管理员', '系统管理员'] },
      },
      {
        path: 'dashboard',
        name: 'admin-dashboard',
        component: () => import('@/views/admin/DashboardView.vue'),
        meta: { title: '数据看板', roles: ['自习室管理员'] },
      },
      {
        path: 'rooms',
        name: 'admin-rooms',
        component: () => import('@/views/admin/RoomManageView.vue'),
        meta: { title: '自习室管理', roles: ['自习室管理员'] },
      },
      {
        path: 'seats',
        name: 'admin-seats',
        component: () => import('@/views/admin/SeatManageView.vue'),
        meta: { title: '座位管理', roles: ['自习室管理员'] },
      },
      {
        path: 'reservations',
        name: 'admin-reservations',
        component: () => import('@/views/admin/ReservationManageView.vue'),
        meta: { title: '预约管理', roles: ['自习室管理员'] },
      },
      {
        path: 'violations',
        name: 'admin-violations',
        component: () => import('@/views/admin/ViolationManageView.vue'),
        meta: { title: '违约管理', roles: ['自习室管理员'] },
      },
      {
        path: 'complaints',
        name: 'admin-complaints',
        component: () => import('@/views/admin/ComplaintManageView.vue'),
        meta: { title: '投诉处理', roles: ['自习室管理员'] },
      },
      {
        path: 'users',
        name: 'admin-users',
        component: () => import('@/views/admin/UserManageView.vue'),
        meta: { title: '用户管理', roles: ['自习室管理员'] },
      },
      {
        path: 'blacklist',
        name: 'admin-blacklist',
        component: () => import('@/views/admin/BlacklistManageView.vue'),
        meta: { title: '黑名单管理', roles: ['自习室管理员'] },
      },
    ],
  },
  {
    path: '/',
    redirect: () =>
        useAuthStore().isAdmin ? '/admin/dashboard'
          : useAuthStore().isSystemAdmin ? '/admin/notice'
          : '/student/home',
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: () => import('@/views/NotFoundView.vue'),
      meta: { public: true },
    },
  ]

  const router = createRouter({
    history: createWebHistory(),
    routes,
  })

router.beforeEach((to) => {
  const auth = useAuthStore()

  if (to.meta.public) return true
  if (!auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  const roles = to.meta.roles as Role[] | undefined
  if (roles && auth.user && !roles.includes(auth.user.role)) {
    // 角色不符：按身份回到各自的合法首页，避免越权进入或误导向学生端
    if (auth.isAdmin) return '/admin/dashboard'
    if (auth.isSystemAdmin) return '/admin/notice'
    return '/student/home'
  }
  return true
})

export default router
