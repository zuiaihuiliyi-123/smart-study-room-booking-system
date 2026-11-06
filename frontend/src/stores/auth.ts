import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getMe, login as loginApi, register as registerApi } from '@/api/auth'
import type { CurrentUser, LoginRequest, RegisterRequest } from '@/types'

const TOKEN_KEY = 'ssr_token'
const USER_KEY = 'ssr_user'

/** 令牌可能落在 localStorage（记住我）或 sessionStorage（关浏览器即失效）。 */
function readToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY) ?? ''
}

function readCachedUser(): CurrentUser | null {
  const raw = localStorage.getItem(USER_KEY) ?? sessionStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw) as CurrentUser
  } catch {
    return null
  }
}

/** 清空两种存储中的凭据，避免「记住我」与「不记住」之间残留。 */
function clearCredentials(): void {
  for (const storage of [localStorage, sessionStorage]) {
    storage.removeItem(TOKEN_KEY)
    storage.removeItem(USER_KEY)
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(readToken())
  const user = ref<CurrentUser | null>(readCachedUser())

  /**
   * 是否「记住我」：决定凭据写入 localStorage（跨浏览器会话保留）还是 sessionStorage（关闭标签页即失效）。
   * 初始值从「令牌当前在哪种存储」推断，便于刷新后保持一致。
   */
  let rememberMe = Boolean(localStorage.getItem(TOKEN_KEY))

  function persist(key: string, value: string): void {
    ;(rememberMe ? localStorage : sessionStorage).setItem(key, value)
  }

  const isLoggedIn = computed(() => Boolean(token.value))
  // 业务管理员（R-02）：拥有看板、资源、预约、违约、投诉、用户、黑名单等业务管理权限。
  // 系统管理员（R-04）本版无业务操作权限（课程结构版 §4.1.1 定稿矩阵），
  // 仅未来"全局参数配置"接口归其所有（本期未实现），故不并入 isAdmin。
  const isAdmin = computed(() => user.value?.role === '自习室管理员')
  const isSystemAdmin = computed(() => user.value?.role === '系统管理员')

  /**
   * 登录并持久化凭据。
   * @param rememberMe 勾选「记住我」时令牌写入 localStorage；否则写入 sessionStorage
   *        （自习室常见共用机房：不勾选时关闭浏览器即失效，降低冒用风险）。
   */
  async function login(payload: LoginRequest, remember = false) {
    const data = await loginApi(payload)
    rememberMe = remember
    clearCredentials()
    token.value = data.access_token
    persist(TOKEN_KEY, data.access_token)
    await fetchMe()
  }

  /** 学生自助注册：后端创建「学生用户」并直接签发令牌，注册即登录（不跨会话保留）。 */
  async function register(payload: RegisterRequest) {
    const data = await registerApi(payload)
    rememberMe = false
    clearCredentials()
    token.value = data.access_token
    persist(TOKEN_KEY, data.access_token)
    await fetchMe()
  }

  async function fetchMe() {
    user.value = await getMe()
    persist(USER_KEY, JSON.stringify(user.value))
  }

  function logout() {
    token.value = ''
    user.value = null
    clearCredentials()
  }

  return { token, user, isLoggedIn, isAdmin, isSystemAdmin, login, register, fetchMe, logout }
})
