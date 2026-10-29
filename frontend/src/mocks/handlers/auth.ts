/**
 * 认证相关 mock：POST /auth/login、GET /auth/me。
 *
 * 与 backend/app/services/auth_service.py 一致：
 * 口令错误 401（中文 message）、账户停用 403、登录成功只返回 access_token。
 */
import { http } from 'msw'

import type { LoginRequest, TokenResponse } from '@/types'

import { createSession, findUserByStudentNo, publicUser } from '../db'
import { abort, json, readBody, requireUser, safe } from '../http'

export const authHandlers = [
  http.post('/api/v1/auth/login', ({ request }) =>
      safe(async () => {
      const payload = await readBody<Partial<LoginRequest>>(request)
      const studentNo = (payload.student_no ?? '').trim()
      const password = typeof payload.password === 'string' ? payload.password : ''
      const user = findUserByStudentNo(studentNo)

      if (!user || password === '' || user.password !== password) {
        return abort(401, 'INVALID_CREDENTIALS', '学号或密码错误')
      }
      if (user.account_status === '停用') {
        return abort(403, 'ACCOUNT_DISABLED', '账户已停用，请联系管理员')
      }

      const body: TokenResponse = {
        access_token: createSession(user.id),
        token_type: 'bearer',
      }
      return json(body)
    }),
),

http.get('/api/v1/auth/me', ({ request }) =>
    safe(() => json(publicUser(requireUser(request)))),
),
]
