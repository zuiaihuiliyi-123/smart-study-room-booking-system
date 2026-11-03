import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getMe, login as loginApi, register as registerApi } from '@/api/auth'
import type { CurrentUser, LoginRequest, RegisterRequest } from '@/types'

const TOKEN_KEY = 'ssr_token'
const USER_KEY = 'ssr_user'

function readCachedUser(): CurrentUser | null {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as CurrentUser
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem(TOKEN_KEY) ?? '')
  const user = ref<CurrentUser | null>(readCachedUser())

  const isLoggedIn = computed(() => Boolean(token.value))
  // 业务管理员（R-02）：拥有看板、资源、预约、违约、投诉、用户、黑名单等业务管理权限。
  // 系统管理员（R-04）本版无业务操作权限（课程结构版 §4.1.1 定稿矩阵），
  // 仅未来"全局参数配置"接口归其所有（本期未实现），故不并入 isAdmin。
  const isAdmin = computed(() => user.value?.role === '自习室管理员')
  const isSystemAdmin = computed(() => user.value?.role === '系统管理员')

  async function login(payload: LoginRequest) {
    const data = await loginApi(payload)
    token.value = data.access_token
    localStorage.setItem(TOKEN_KEY, data.access_token)
    await fetchMe()
  }

  /** 学生自助注册：后端创建「学生用户」并直接签发令牌，注册即登录 */
  async function register(payload: RegisterRequest) {
    const data = await registerApi(payload)
    token.value = data.access_token
    localStorage.setItem(TOKEN_KEY, data.access_token)
    await fetchMe()
  }

  async function fetchMe() {
    user.value = await getMe()
    localStorage.setItem(USER_KEY, JSON.stringify(user.value))
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, user, isLoggedIn, isAdmin, isSystemAdmin, login, register, fetchMe, logout }
})
