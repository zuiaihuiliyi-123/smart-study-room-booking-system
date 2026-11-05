/**
 * 黑名单接口（FR-044 / ST-041、ST-043）。
 *
 * 本文件是**新增**模块：`src/mocks/handlers/blacklist.ts` 与
 * `backend/app/api/v1/blacklist.py` 的路径早已就位，但 `src/api/` 一直缺少对应封装。
 * 路径与后端逐字一致，未改动任何既有 API 路径。
 */
import { http } from './request'
import type { BlacklistEntry, PageResult } from '@/types'

/**
 * 记录状态：生效中（未解除；手动限制到期后仍生效）/ 已解除 / 已过期（仅自动限制到期）。
 */
export type BlacklistState = '生效中' | '已解除' | '已过期'

export interface BlacklistQuery {
  state?: BlacklistState | ''
  mode?: '自动' | '手动' | ''
  /** 按用户过滤；黑名单页从「用户管理」跳转时带上 */
  user_id?: number
  page?: number
  page_size?: number
}

export const listBlacklist = (params: BlacklistQuery) =>
    http.get<PageResult<BlacklistEntry>>('/blacklist', params)

  /**
   * ST-041：手动加入黑名单（原因必填；期限可选）。
   * `expire_at` 为 null 表示不设期限；手动限制无论是否设期限都不会自动解除，须管理员解除。
   */
  export const addBlacklist = (data: {
    user_id: number
    reason: string
    expire_at: string | null
  }) => http.post<BlacklistEntry>('/blacklist', data)

/** ST-043：手动解除（原因必填，后端写入 `release_reason` 与审计日志）。 */
export const releaseBlacklist = (entryId: number, data: { reason: string }) =>
    http.post<BlacklistEntry>(`/blacklist/${entryId}/release`, data)
