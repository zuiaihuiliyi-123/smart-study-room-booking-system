/**
 * 违约 mock：GET /violations/me、GET /violations、POST /violations/manual。
 *
 * 手动违约登记（FR-023 / BR-015）：仅「使用中」预约、必填原因、记录操作人；
 * 与管理员强制取消（仅「待使用」）互斥；登记后累计违约达到 3 次自动限制 7 天（BR-009 / BR-010）。
 */
import { http } from 'msw'

import type { Violation } from '@/types'

import { getDb, nextId, recountViolations, pushMessage, restrictUser } from '../db'
import { abort, fromError, json, pageOf, readBody, requireAdmin, requireUser, safe, strParam } from '../http'
import { RULES, validateManualViolation } from '../rules'
import { formatDateTime, serverNow } from '../time'

function sortByCreatedDesc<T extends { created_at: string }>(items: readonly T[]): T[] {
  return [...items].sort((left, right) =>
      left.created_at === right.created_at ? 0 : left.created_at < right.created_at ? 1 : -1,
  )
}

export const violationHandlers = [
  http.get('/api/v1/violations/me', ({ request }) =>
      safe(() => {
      const user = requireUser(request)
      const query = new URL(request.url).searchParams
      const mine = getDb().violations.filter((item) => item.user_id === user.id)
      return json(pageOf(sortByCreatedDesc(mine), query))
    }),
),

/**
 * FR-032 管理端口径：按「违约类型 / 时间区间 / 学号」筛选全部记录。
 * 后端 `GET /violations` 目前只有分页参数，其余为待补参数（见接口缺口清单）。
 */
http.get('/api/v1/violations', ({ request }) =>
    safe(() => {
    requireAdmin(request)
    const db = getDb()
    const query = new URL(request.url).searchParams
    const type = strParam(query, 'type')
    const studentNo = strParam(query, 'student_no')
    const from = strParam(query, 'created_from')
    const to = strParam(query, 'created_to')
    const userIds =
      studentNo === ''
      ? null
      : new Set(
      db.users.filter((item) => item.student_no === studentNo).map((item) => item.id),
    )

    const filtered = db.violations.filter((item) => {
      if (type !== '' && item.type !== type) return false
      if (userIds !== null && !userIds.has(item.user_id)) return false
      const day = item.created_at.slice(0, 10)
      if (from !== '' && day < from) return false
      if (to !== '' && day > to) return false
      return true
    })
  return json(pageOf(sortByCreatedDesc(filtered), query))
}),
),

http.post('/api/v1/violations/manual', ({ request }) =>
    safe(async () => {
    const admin = requireAdmin(request)
    const db = getDb()
    const payload = await readBody<{ reservation_id?: number; reason?: string }>(request)
    const reason = (payload.reason ?? '').trim()
    if (reason === '') {
      return abort(400, 'INVALID_ARGUMENT', '手动违约登记必须填写原因')
    }

    const record = db.reservations.find((item) => item.id === Number(payload.reservation_id))
    if (!record) return abort(404, 'RESERVATION_NOT_FOUND', '预约单不存在')
    const target = db.users.find((item) => item.id === record.user_id)
    if (!target) return abort(404, 'USER_NOT_FOUND', '预约单对应的用户不存在')

    const result = validateManualViolation(record)
    if (!result.ok) return fromError(result.error)

    record.status = '已违约'
    record.updated_at = formatDateTime(serverNow())

    const violation: Violation = {
      id: nextId(db.violations),
      user_id: target.id,
      reservation_id: record.id,
      type: '手动违约',
      reason,
      operator_id: admin.id,
      created_at: formatDateTime(serverNow()),
    }
    db.violations.push(violation)

    const count = recountViolations(target.id)
    pushMessage(target.id, {
      type: '违约通知',
      title: '违约记录已登记',
      content: `管理员对你的预约（${record.reserve_date} ${record.start_time.slice(0, 5)}–${record.end_time.slice(0, 5)}）登记了手动违约：${reason}。当前累计违约 ${count} 次。`,
        relatedType: '违约记录',
        relatedId: violation.id,
      })

      if (count >= RULES.violationThreshold && target.account_status !== '受限') {
        const entry = restrictUser(
          target,
          `累计有效违约达到 ${RULES.violationThreshold} 次，系统自动限制 ${RULES.restrictionDays} 天`,
    )
    pushMessage(target.id, {
      type: '系统通知',
      title: '账户已被限制',
      content: `你的累计违约已达 ${count} 次，账户自 ${entry.start_at.replace('T', ' ').slice(0, 16)} 起限制 ${RULES.restrictionDays} 天。`,
          relatedType: '黑名单',
          relatedId: entry.id,
        })
      }

      return json(violation)
    }),
  ),
]
