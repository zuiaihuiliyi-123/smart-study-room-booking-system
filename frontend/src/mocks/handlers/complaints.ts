/**
 * 投诉 mock：POST /complaints、GET /complaints/me、GET /complaints、PATCH /complaints/{id}。
 * 对齐 backend/app/api/v1/complaints.py：新建返回 201，提交后初始状态「待处理」。
 */
import { http } from 'msw'

import type { Complaint } from '@/types'

import { getDb, nextId, pushMessage } from '../db'
import { abort, json, pageOf, param, readBody, requireAdmin, requireUser, safe, strParam } from '../http'
import { formatDateTime, serverNow } from '../time'

const TARGET_TYPES: readonly string[] = ['座位', '自习室', '预约单', '用户']
const HANDLE_STATUSES: readonly Complaint['status'][] = [
  '待处理',
  '处理中',
  '已处理',
  '已驳回',
  '已关闭',
]

/**
 * 管理员可执行的状态流转（严格照第 5.4 节状态转换表，不自行放宽）：
 * - ST-060：待处理 → 处理中（受理）；
 * - ST-061：待处理 → 已驳回（必填驳回理由）；
 * - ST-062：处理中 → 已处理（必填处理说明）；
 * - ST-063：已处理 → 已关闭由**投诉人确认 / 系统超时**触发，管理员不可直接置为「已关闭」。
 */
const ADMIN_TRANSITIONS: Record<Complaint['status'], Complaint['status'][]> = {
  待处理: ['处理中', '已驳回'],
  处理中: ['已处理'],
  已处理: [],
  已驳回: [],
  已关闭: [],
}

function sortByCreatedDesc(items: readonly Complaint[]): Complaint[] {
  return [...items].sort((left, right) =>
      left.created_at === right.created_at ? 0 : left.created_at < right.created_at ? 1 : -1,
  )
}

export const complaintHandlers = [
  http.post('/api/v1/complaints', ({ request }) =>
      safe(async () => {
      const user = requireUser(request)
      const db = getDb()
      const payload = await readBody<{ target_type?: string; target_id?: number; content?: string }>(
        request,
      )
      const targetType = (payload.target_type ?? '').trim()
      const targetId = Number(payload.target_id)
      const content = (payload.content ?? '').trim()

      if (!TARGET_TYPES.includes(targetType)) {
        return abort(400, 'INVALID_ARGUMENT', '投诉对象类型只能是「座位 / 自习室 / 预约单 / 用户」')
      }
      if (!Number.isInteger(targetId) || targetId <= 0) {
        return abort(400, 'INVALID_ARGUMENT', '投诉对象编号不合法')
      }
      if (content === '') return abort(400, 'INVALID_ARGUMENT', '投诉内容不能为空')
      if (content.length > 1000) {
        return abort(400, 'INVALID_ARGUMENT', '投诉内容不能超过 1000 字')
      }

      const complaint: Complaint = {
        id: nextId(db.complaints),
        user_id: user.id,
        target_type: targetType,
        target_id: targetId,
        content,
        status: '待处理',
        handler_id: null,
        handle_note: null,
        handled_at: null,
        created_at: formatDateTime(serverNow()),
      }
      db.complaints.push(complaint)
      return json(complaint, 201)
    }),
),

http.get('/api/v1/complaints/me', ({ request }) =>
    safe(() => {
    const user = requireUser(request)
    const query = new URL(request.url).searchParams
    const mine = getDb().complaints.filter((item) => item.user_id === user.id)
    return json(pageOf(sortByCreatedDesc(mine), query))
  }),
),

/**
 * FR-043 管理端队列：按状态 / 对象类型 / 提交时间区间筛选。
 * 后端 `GET /complaints` 目前只有分页参数，其余为待补参数（见接口缺口清单）。
 */
http.get('/api/v1/complaints', ({ request }) =>
    safe(() => {
    requireAdmin(request)
    const query = new URL(request.url).searchParams
    const status = strParam(query, 'status')
    const targetType = strParam(query, 'target_type')
    const from = strParam(query, 'created_from')
    const to = strParam(query, 'created_to')

    const filtered = getDb().complaints.filter((item) => {
      if (status !== '' && item.status !== status) return false
      if (targetType !== '' && item.target_type !== targetType) return false
      const day = item.created_at.slice(0, 10)
      if (from !== '' && day < from) return false
      if (to !== '' && day > to) return false
      return true
    })
  return json(pageOf(sortByCreatedDesc(filtered), query))
}),
),

http.patch('/api/v1/complaints/:complaintId', ({ request, params }) =>
    safe(async () => {
    const admin = requireAdmin(request)
    const db = getDb()
    const complaint = db.complaints.find((item) => item.id === Number(param(params, 'complaintId')))
    if (!complaint) return abort(404, 'COMPLAINT_NOT_FOUND', '投诉不存在')

    const payload = await readBody<{ status?: Complaint['status']; handle_note?: string }>(request)
    const status = payload.status
    const note = (payload.handle_note ?? '').trim()
    if (status === undefined || !HANDLE_STATUSES.includes(status)) {
      return abort(400, 'INVALID_ARGUMENT', '投诉状态只能是「待处理 / 处理中 / 已处理 / 已驳回 / 已关闭」')
    }
    if (note === '') return abort(400, 'INVALID_ARGUMENT', '处理说明不能为空')

    const allowed = ADMIN_TRANSITIONS[complaint.status]
    if (!allowed.includes(status)) {
      const next =
        allowed.length > 0 ? `只能流转到「${allowed.join(' / ')}」` : '该状态已是终态或只能由投诉人 / 系统推进'
      return abort(409, 'STATE_NOT_ALLOWED', `投诉当前为「${complaint.status}」，${next}`)
    }

  complaint.status = status
  complaint.handler_id = admin.id
  complaint.handle_note = note
  complaint.handled_at = formatDateTime(serverNow())

  pushMessage(complaint.user_id, {
    type: '投诉反馈',
    title: `投诉已${status}`,
        content: `你对${complaint.target_type}的投诉（#${complaint.id}）状态更新为「${status}」。处理说明：${note}`,
    relatedType: '投诉',
    relatedId: complaint.id,
  })

return json(complaint)
}),
),

/** ST-063：投诉人确认处理结果，将「已处理」投诉关闭。 */
http.post('/api/v1/complaints/:complaintId/confirm', ({ request, params }) =>
    safe(() => {
    const user = requireUser(request)
    const complaint = getDb().complaints.find(
      (item) => item.id === Number(param(params, 'complaintId')),
    )
    if (!complaint) return abort(404, 'COMPLAINT_NOT_FOUND', '投诉不存在')
    if (complaint.user_id !== user.id) {
      return abort(403, 'COMPLAINT_NOT_OWNER', '只能确认本人的投诉')
    }
    if (complaint.status !== '已处理') {
      return abort(
        409,
        'STATE_NOT_ALLOWED',
        `投诉当前为「${complaint.status}」，只有「已处理」的投诉可以确认关闭`,
      )
    }

    complaint.status = '已关闭'
    return json(complaint)
  }),
),
]
