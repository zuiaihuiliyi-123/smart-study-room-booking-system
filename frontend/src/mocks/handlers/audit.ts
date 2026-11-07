/**
 * 审计日志 mock：GET /audit-logs（管理员只读）。
 * 支持操作类型、操作人、目标类型与操作日期筛选，与后端口径一致。
 */
import { http } from 'msw'

import type { AuditLog } from '@/types'

import { getDb } from '../db'
import { intParam, json, pageOf, requireAdmin, safe, strParam } from '../http'

function dayOf(value: string): string {
  return value.slice(0, 10)
}

export const auditHandlers = [
  http.get('/api/v1/audit-logs', ({ request }) =>
    safe(() => {
      requireAdmin(request)
      const query = new URL(request.url).searchParams
      const actionType = strParam(query, 'action_type')
      const targetType = strParam(query, 'target_type')
      const operatorId = intParam(query, 'operator_id', Number.NaN)
      const createdFrom = strParam(query, 'created_from')
      const createdTo = strParam(query, 'created_to')

      const filtered = getDb().audit_logs.filter((item: AuditLog) => {
        if (actionType !== '' && item.action_type !== actionType) return false
        if (targetType !== '' && item.target_type !== targetType) return false
        if (Number.isFinite(operatorId) && item.operator_id !== operatorId) return false
        const day = dayOf(item.created_at)
        if (createdFrom !== '' && day < createdFrom) return false
        if (createdTo !== '' && day > createdTo) return false
        return true
      })

      return json(pageOf([...filtered].sort((left, right) => right.id - left.id), query))
    }),
  ),
]
