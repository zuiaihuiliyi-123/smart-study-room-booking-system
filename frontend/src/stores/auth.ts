import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { getMe, login as loginApi } from '@/api/auth'
import type { CurrentUser, LoginRequest } from '@/types'

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
  const isAdmin = computed(
    () => user.value?.role === '自习室管理员' || user.value?.role === '系统管理员',
  )

  async function login(payload: LoginRequest) {
    const data = await loginApi(payload)
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

  return { token, user, isLoggedIn, isAdmin, login, fetchMe, logout }
})
