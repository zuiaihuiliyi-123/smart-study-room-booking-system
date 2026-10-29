/**
 * 用户 mock：GET /users/me、PATCH /users/me、GET /users。
 *
 * FR-040 / BR-018：身份字段（姓名、学号、角色）只读，仅联系方式可改；
 * 管理员可查询用户列表与账户状态，但不提供编辑身份信息的入口。
 * 联系方式是否脱敏由界面决定（NFR-006），mock 与后端一样返回原值。
 */
import { http } from 'msw'

import { getDb, publicUser } from '../db'
import {
  abort,
  intParam,
  json,
  pageOf,
  readBody,
  requireAdmin,
  requireUser,
  safe,
  strParam,
} from '../http'

export const userHandlers = [
  http.get('/api/v1/users/me', ({ request }) =>
      safe(() => json(publicUser(requireUser(request)))),
  ),

  http.patch('/api/v1/users/me', ({ request }) =>
      safe(async () => {
      const user = requireUser(request)
      const payload = await readBody<{ contact?: string | null }>(request)

      if (payload.contact !== undefined) {
        if (payload.contact !== null && typeof payload.contact !== 'string') {
          return abort(400, 'INVALID_ARGUMENT', '联系方式格式不合法')
        }
        if (typeof payload.contact === 'string' && payload.contact.length > 100) {
          return abort(400, 'INVALID_ARGUMENT', '联系方式不能超过 100 字')
        }
        const contact = payload.contact === null ? '' : payload.contact.trim()
        user.contact = contact === '' ? null : contact
      }

      return json(publicUser(user))
    }),
),

/**
 * FR-040：管理员查询用户列表。
 * 本接口只读——管理员**不提供**编辑姓名 / 学号的入口（BR-018 本版裁定）；
 * 联系方式是否脱敏由界面决定（NFR-006），mock 与后端一样返回原值。
 * 查询参数（keyword / role / account_status / violation_min）为待补参数。
 */
http.get('/api/v1/users', ({ request }) =>
    safe(() => {
    requireAdmin(request)
    const query = new URL(request.url).searchParams
    const keyword = strParam(query, 'keyword').toLowerCase()
    const role = strParam(query, 'role')
    const accountStatus = strParam(query, 'account_status')
    const violationMin = intParam(query, 'violation_min', Number.NaN)

    const filtered = getDb()
      .users.map(publicUser)
      .filter((user) => {
      if (
        keyword !== '' &&
          !user.name.toLowerCase().includes(keyword) &&
          !user.student_no.toLowerCase().includes(keyword)
      ) {
        return false
      }
      if (role !== '' && user.role !== role) return false
      if (accountStatus !== '' && user.account_status !== accountStatus) return false
      if (Number.isFinite(violationMin) && user.violation_count < violationMin) return false
      return true
    })
  return json(pageOf(filtered, query))
}),
),
]
