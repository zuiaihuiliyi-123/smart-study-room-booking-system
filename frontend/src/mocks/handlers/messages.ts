/**
 * 站内消息 mock：GET /messages/me、POST /messages/{id}/read（FR-060 / SCOPE-07）。
 * 只做站内列表与已读标记，不接短信 / 邮件 / 微信。
 */
import { http } from 'msw'

import { getDb, publicMessage } from '../db'
import { abort, json, pageOf, param, requireUser, safe } from '../http'

function sortByCreatedDesc<T extends { created_at: string }>(items: readonly T[]): T[] {
  return [...items].sort((left, right) =>
      left.created_at === right.created_at ? 0 : left.created_at < right.created_at ? 1 : -1,
  )
}

export const messageHandlers = [
  http.get('/api/v1/messages/me', ({ request }) =>
      safe(() => {
      const user = requireUser(request)
      const query = new URL(request.url).searchParams
      const mine = getDb()
        .messages.filter((item) => item.user_id === user.id)
        .map(publicMessage)
      return json(pageOf(sortByCreatedDesc(mine), query))
    }),
),

/**
 * 未读数：分页后列表不再包含全部消息，角标必须单独取。
 * 与 `GET /messages/me` 分开注册，避免被 `:messageId` 类路由抢先匹配。
 */
http.get('/api/v1/messages/unread-count', ({ request }) =>
    safe(() => {
    const user = requireUser(request)
    const count = getDb().messages.filter(
      (item) => item.user_id === user.id && !item.is_read,
    ).length
    return json({ count })
  }),
),

http.post('/api/v1/messages/:messageId/read', ({ request, params }) =>
    safe(() => {
    const user = requireUser(request)
    const message = getDb().messages.find(
      (item) => item.id === Number(param(params, 'messageId')),
    )
    if (!message) return abort(404, 'MESSAGE_NOT_FOUND', '站内消息不存在')
    if (message.user_id !== user.id) {
      return abort(403, 'MESSAGE_NOT_OWNED', '只能操作本人的站内消息')
    }
    message.is_read = true
    return json(publicMessage(message))
  }),
),
]
