import { http } from './request'
import type { CurrentUser, PageResult } from '@/types'

/** 管理端用户查询（FR-040）：姓名 / 学号关键词、角色、账户状态、累计违约次数下限。 */
export interface UserQuery {
  /** 姓名或学号的关键词（模糊匹配） */
  keyword?: string
  role?: string
  account_status?: string
  /** 累计违约次数下限（≥） */
  violation_min?: number
  page?: number
  page_size?: number
}

export const getMyProfile = () => http.get<CurrentUser>('/users/me')

export const updateMyProfile = (data: { contact?: string }) =>
    http.patch<CurrentUser>('/users/me', data)

  export const listUsers = (params: UserQuery) =>
      http.get<PageResult<CurrentUser>>('/users', params)

/** 管理员停用 / 恢复账户（ST-044 / ST-045 / ST-046），须填写原因（NFR-009）。 */
export interface AccountStatusUpdate {
  /** 目标状态：停用（封禁登录）或 正常（恢复） */
  account_status: '停用' | '正常'
  /** 变更原因，写入审计日志 */
  reason: string
}

export const updateUserAccountStatus = (userId: number, data: AccountStatusUpdate) =>
    http.patch<CurrentUser>(`/users/${userId}/account-status`, data)
