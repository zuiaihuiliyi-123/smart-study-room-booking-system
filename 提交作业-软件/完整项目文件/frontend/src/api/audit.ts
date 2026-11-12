import { http } from './request'
import type { AuditLog, PageResult } from '@/types'

/** 审计日志查询（NFR-009）：操作类型 / 操作人 / 目标类型 / 操作日期区间。 */
export interface AuditQuery {
  action_type?: string
  operator_id?: number
  target_type?: string
  created_from?: string
  created_to?: string
  page?: number
  page_size?: number
}

/** 管理员只读查询审计日志。 */
export const listAuditLogs = (params: AuditQuery) =>
  http.get<PageResult<AuditLog>>('/audit-logs', params)
