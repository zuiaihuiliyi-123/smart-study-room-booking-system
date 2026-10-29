/**
 * 评价 mock：POST /reviews、GET /reviews/me、GET /reviews。
 * BR-013：仅本人「已完成」预约可评价，一单一评，评分 1～5；新建返回 201。
 */
import { http } from 'msw'

import type { Review } from '@/types'

import { getDb, nextId } from '../db'
import { abort, fromError, json, pageOf, readBody, requireAdmin, requireUser, safe } from '../http'
import { validateReview } from '../rules'
import { formatDateTime, serverNow } from '../time'

function sortByCreatedDesc(items: readonly Review[]): Review[] {
  return [...items].sort((left, right) =>
      left.created_at === right.created_at ? 0 : left.created_at < right.created_at ? 1 : -1,
  )
}

export const reviewHandlers = [
  http.post('/api/v1/reviews', ({ request }) =>
      safe(async () => {
      const user = requireUser(request)
      const db = getDb()
      const payload = await readBody<{ reservation_id?: number; score?: number; content?: string }>(
        request,
      )

      const score = Number(payload.score)
      if (!Number.isInteger(score) || score < 1 || score > 5) {
        return abort(400, 'INVALID_ARGUMENT', '评分必须是 1～5 的整数')
      }
      const content = (payload.content ?? '').trim()
      if (content.length > 500) {
        return abort(400, 'INVALID_ARGUMENT', '评价内容不能超过 500 字')
      }

      const result = validateReview(db, user, Number(payload.reservation_id))
      if (!result.ok) return fromError(result.error)

      const review: Review = {
        id: nextId(db.reviews),
        user_id: user.id,
        reservation_id: result.value.id,
        score,
        content: content === '' ? null : content,
        created_at: formatDateTime(serverNow()),
      }
      db.reviews.push(review)
      return json(review, 201)
    }),
),

http.get('/api/v1/reviews/me', ({ request }) =>
    safe(() => {
    const user = requireUser(request)
    const query = new URL(request.url).searchParams
    const mine = getDb().reviews.filter((item) => item.user_id === user.id)
    return json(pageOf(sortByCreatedDesc(mine), query))
  }),
),

http.get('/api/v1/reviews', ({ request }) =>
    safe(() => {
    requireAdmin(request)
    const query = new URL(request.url).searchParams
    return json(pageOf(sortByCreatedDesc(getDb().reviews), query))
  }),
),
]
