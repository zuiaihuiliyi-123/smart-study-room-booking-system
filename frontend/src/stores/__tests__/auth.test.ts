import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import * as authApi from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import type { CurrentUser } from '@/types'

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  register: vi.fn(),
  getMe: vi.fn(),
  changePassword: vi.fn(),
}))

const user: CurrentUser = {
  id: 1,
  name: '演示学生',
  student_no: 'student',
  role: '学生用户',
  account_status: '正常',
  violation_count: 0,
  contact: '13800001234',
}

beforeEach(() => {
  setActivePinia(createPinia())
  vi.clearAllMocks()
  localStorage.clear()
  sessionStorage.clear()
})

describe('auth store 登录与持久化', () => {
  it('勾选记住我时 token/user 写入 localStorage', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ access_token: 'token-1', token_type: 'bearer' })
    vi.mocked(authApi.getMe).mockResolvedValue(user)

    const store = useAuthStore()
    await store.login({ student_no: 'student', password: 'student123' }, true)

    expect(store.isLoggedIn).toBe(true)
    expect(store.user).toEqual(user)
    expect(localStorage.getItem('ssr_token')).toBe('token-1')
    expect(localStorage.getItem('ssr_user')).toContain('演示学生')
    expect(sessionStorage.getItem('ssr_token')).toBeNull()
  })

  it('不记住我时 token/user 写入 sessionStorage', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ access_token: 'token-2', token_type: 'bearer' })
    vi.mocked(authApi.getMe).mockResolvedValue(user)

    const store = useAuthStore()
    await store.login({ student_no: 'student', password: 'student123' })

    expect(sessionStorage.getItem('ssr_token')).toBe('token-2')
    expect(localStorage.getItem('ssr_token')).toBeNull()
  })

  it('初始化时从本地存储恢复登录态', () => {
    localStorage.setItem('ssr_token', 'cached-token')
    localStorage.setItem('ssr_user', JSON.stringify(user))

    const store = useAuthStore()
    expect(store.isLoggedIn).toBe(true)
    expect(store.user?.student_no).toBe('student')
    expect(store.isAdmin).toBe(false)
    expect(store.isSystemAdmin).toBe(false)
  })

  it('登出时清空两种存储与内存状态', async () => {
    vi.mocked(authApi.login).mockResolvedValue({ access_token: 'token-3', token_type: 'bearer' })
    vi.mocked(authApi.getMe).mockResolvedValue(user)
    const store = useAuthStore()
    await store.login({ student_no: 'student', password: 'student123' }, true)

    store.logout()

    expect(store.isLoggedIn).toBe(false)
    expect(store.user).toBeNull()
    expect(localStorage.getItem('ssr_token')).toBeNull()
    expect(localStorage.getItem('ssr_user')).toBeNull()
    expect(sessionStorage.getItem('ssr_token')).toBeNull()
  })
})

describe('auth store 修改密码', () => {
  it('改密后用新 token 覆盖原存储位置，保持当前设备登录', async () => {
    localStorage.setItem('ssr_token', 'old-token')
    vi.mocked(authApi.changePassword).mockResolvedValue({
      access_token: 'new-token',
      token_type: 'bearer',
    })

    const store = useAuthStore()
    await store.changePassword({ old_password: 'old', new_password: 'new' })

    expect(store.token).toBe('new-token')
    expect(localStorage.getItem('ssr_token')).toBe('new-token')
    expect(sessionStorage.getItem('ssr_token')).toBeNull()
  })
})

describe('auth store 角色判断', () => {
  it('管理员与系统管理员分别由 role 判定', () => {
    localStorage.setItem('ssr_token', 'token')
    localStorage.setItem(
      'ssr_user',
      JSON.stringify({ ...user, role: '自习室管理员' } satisfies CurrentUser),
    )
    const adminStore = useAuthStore()
    expect(adminStore.isAdmin).toBe(true)
    expect(adminStore.isSystemAdmin).toBe(false)

    setActivePinia(createPinia())
    localStorage.setItem('ssr_token', 'token')
    localStorage.setItem(
      'ssr_user',
      JSON.stringify({ ...user, role: '系统管理员' } satisfies CurrentUser),
    )
    const systemStore = useAuthStore()
    expect(systemStore.isAdmin).toBe(false)
    expect(systemStore.isSystemAdmin).toBe(true)
  })
})
