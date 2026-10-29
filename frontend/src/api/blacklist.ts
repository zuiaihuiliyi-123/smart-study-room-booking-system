/**
 * 黑名单接口（FR-044 / ST-041、ST-043）。
 *
 * 本文件是**新增**模块：`src/mocks/handlers/blacklist.ts` 与
 * `backend/app/api/v1/blacklist.py` 的路径早已就位，但 `src/api/` 一直缺少对应封装。
 * 路径与后端逐字一致，未改动任何既有 API 路径。
 */
import { http } from './request'
import type { BlacklistEntry, PageResult } from '@/types'

/** 记录状态：生效中（未解除且未到期）/ 已解除（管理员手动解除）/ 已过期（到期自动失效） */
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
   * ST-041：手动加入黑名单（原因必填 + 期限）。
   * `expire_at` 为 null 时由后端按 BR-010 的 7 天给出默认期限。
   */
  export const addBlacklist = (data: {
    user_id: number
    reason: string
    expire_at: string | null
  }) => http.post<BlacklistEntry>('/blacklist', data)

/**
 * ST-043：手动解除（原因必填）。
 * 后端 `release_entry` 目前不接收请求体，解除原因只进 `audit_logs`（NFR-009）；
 * 请求体字段属**待补接口**，见交付说明的接口缺口清单。
 */
export const releaseBlacklist = (entryId: number, data: { reason: string }) =>
    http.post<BlacklistEntry>(`/blacklist/${entryId}/release`, data)
