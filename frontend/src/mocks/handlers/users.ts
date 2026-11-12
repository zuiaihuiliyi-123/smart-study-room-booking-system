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
  param,
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
/**
 * FR-040 / ST-044～ST-046：管理员停用 / 恢复学生账户。
 *
 * 与后端一致：只维护学生账户；管理员/系统管理员只读；不能操作自己；
 * 「受限」只能由黑名单产生，账户状态接口只接受正常/停用。
 */
http.patch('/api/v1/users/:userId/account-status', ({ request, params }) =>
    safe(async () => {
    const admin = requireAdmin(request)
    const targetId = Number(param(params, 'userId'))
    if (!Number.isInteger(targetId)) {
      return abort(400, 'INVALID_ARGUMENT', '用户参数不合法')
    }
    const payload = await readBody<{ account_status?: string; reason?: string }>(request)
    const db = getDb()
    const target = db.users.find((item) => item.id === targetId)
    if (!target) return abort(404, 'USER_NOT_FOUND', '用户不存在')

    if (target.id === admin.id) {
      return abort(403, 'SELF_OPERATION_FORBIDDEN', '不能停用或恢复自己的账户')
    }
    if (target.role !== '学生用户') {
      return abort(
        403,
        'TARGET_ROLE_NOT_ALLOWED',
        '管理员账号由信息中心/系统管理员维护，业务管理员不能停用或恢复',
      )
    }
    if (target.account_status === '受限') {
      return abort(
        409,
        'ACCOUNT_STILL_RESTRICTED',
        '该账户当前为「受限」，请先在黑名单管理中解除限制',
      )
    }

    const nextStatus = payload.account_status
    if (nextStatus !== '正常' && nextStatus !== '停用') {
      return abort(400, 'ACCOUNT_STATUS_INVALID', '账户状态只能是正常或停用')
    }
    if (nextStatus === target.account_status) {
      return abort(
        409,
        'ACCOUNT_STATUS_NO_CHANGE',
        `账户当前已是「${target.account_status}」，无需重复操作`,
      )
    }
    const reason = (payload.reason ?? '').trim()
    if (reason === '') {
      return abort(400, 'INVALID_ARGUMENT', '变更原因不能为空')
    }

    target.account_status = nextStatus
    return json(publicUser(target))
  }),
),

]
