/**
 * 黑名单 mock：GET /blacklist、POST /blacklist、POST /blacklist/{id}/release（FR-044）。
 *
 * 路径与 backend/app/api/v1/blacklist.py 完全一致；前端封装见 `src/api/blacklist.ts`。
 * 本文件在既有实现上补了两件事：
 * 1. 列表筛选（state / mode / user_id）——后端目前只有分页参数，属待补参数；
 * 2. 解除时必须带 `reason`（ST-043：解除须记录原因），并回填 `released_reason`
 *    （后端模型暂无该列，解除原因目前只进 `audit_logs`，见接口缺口清单）。
 */
import { http } from 'msw'

import type { BlacklistEntry } from '@/types'

import { getDb, nextId, pushMessage } from '../db'
import { abort, json, pageOf, param, readBody, requireAdmin, safe, strParam } from '../http'
import { RULES, hasActiveRestriction } from '../rules'
import { formatDateTime, serverNow } from '../time'

function sortByStartDesc(items: readonly BlacklistEntry[]): BlacklistEntry[] {
  return [...items].sort((left, right) =>
      left.start_at === right.start_at ? 0 : left.start_at < right.start_at ? 1 : -1,
  )
}

/** 记录状态判定（SM-03 / ST-042）：已解除 → 已解除；未解除且未到期 → 生效中；其余 → 已过期。 */
function stateOf(entry: BlacklistEntry, nowMs: number): '生效中' | '已解除' | '已过期' {
  if (entry.released_at !== null) return '已解除'
  if (entry.expire_at === null) return '生效中'
  return new Date(entry.expire_at).getTime() > nowMs ? '生效中' : '已过期'
}

export const blacklistHandlers = [
  http.get('/api/v1/blacklist', ({ request }) =>
      safe(() => {
      requireAdmin(request)
      const db = getDb()
      const query = new URL(request.url).searchParams
      const state = strParam(query, 'state')
      const mode = strParam(query, 'mode')
      const userIdRaw = strParam(query, 'user_id')
      const userId = userIdRaw === '' ? Number.NaN : Number(userIdRaw)
      const nowMs = serverNow().getTime()

      const filtered = db.blacklist.filter((entry) => {
        if (mode !== '' && entry.mode !== mode) return false
        if (Number.isFinite(userId) && entry.user_id !== userId) return false
        if (state !== '' && stateOf(entry, nowMs) !== state) return false
        return true
      })
    return json(pageOf(sortByStartDesc(filtered), query))
  }),
),

http.post('/api/v1/blacklist', ({ request }) =>
    safe(async () => {
    const admin = requireAdmin(request)
    const db = getDb()
    const payload = await readBody<{
      user_id?: number
      reason?: string
      expire_at?: string | null
    }>(request)

    const reason = (payload.reason ?? '').trim()
    if (reason === '') return abort(400, 'INVALID_ARGUMENT', '手动加入黑名单必须填写原因')
    const target = db.users.find((item) => item.id === Number(payload.user_id))
    if (!target) return abort(404, 'USER_NOT_FOUND', '用户不存在')

    const now = serverNow()
    // `expire_at` 三种情形分开处理：未传 → 按 FR-044 的常见做法给 7 天；
    // 显式传 null → 「不设期限」，只能由管理员手动解除（ST-042）。
    const expireAt =
      payload.expire_at === undefined
      ? formatDateTime(new Date(now.getTime() + RULES.restrictionDays * 86_400_000))
      : payload.expire_at
    const entry: BlacklistEntry = {
      id: nextId(db.blacklist),
      user_id: target.id,
      reason,
      mode: '手动',
      start_at: formatDateTime(now),
      expire_at: expireAt,
      released_at: null,
      operator_id: admin.id,
      released_reason: null,
      released_by: null,
    }
    db.blacklist.push(entry)
    target.account_status = '受限'

    const expireText =
      entry.expire_at === null
      ? '该限制不设期限，需由管理员手动解除'
      : `预计 ${entry.expire_at.replace('T', ' ').slice(0, 16)} 解除`
      pushMessage(target.id, {
        type: '系统通知',
        title: '账户已被限制',
        content: `你的账户已被管理员限制：${reason}，${expireText}。`,
    relatedType: '黑名单',
    relatedId: entry.id,
  })

return json(entry, 201)
}),
),

/** ST-043：管理员移出黑名单，必须填写解除原因（NFR-009 留痕）。 */
http.post('/api/v1/blacklist/:entryId/release', ({ request, params }) =>
    safe(async () => {
    const admin = requireAdmin(request)
    const db = getDb()
    const entry = db.blacklist.find((item) => item.id === Number(param(params, 'entryId')))
    if (!entry) return abort(404, 'ENTRY_NOT_FOUND', '黑名单记录不存在')
    if (entry.released_at !== null) return abort(400, 'ALREADY_RELEASED', '该限制已解除')

    const payload = await readBody<{ reason?: string }>(request)
    const reason = (payload.reason ?? '').trim()
    if (reason === '') return abort(400, 'INVALID_ARGUMENT', '解除限制必须填写原因')

    entry.released_at = formatDateTime(serverNow())
    entry.released_reason = reason
    entry.released_by = admin.id
    const target = db.users.find((item) => item.id === entry.user_id)
    if (target) {
      target.account_status = hasActiveRestriction(db, target.id) ? '受限' : '正常'
      pushMessage(target.id, {
        type: '系统通知',
        title: '账户限制已解除',
        content: `你的账户限制已被管理员解除（原因：${reason}），现在可以正常预约座位。`,
          relatedType: '黑名单',
          relatedId: entry.id,
        })
      }
      return json(entry)
    }),
  ),
]
