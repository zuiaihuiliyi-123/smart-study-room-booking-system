/**
 * 认证相关 mock：POST /auth/register、POST /auth/login、GET /auth/me。
 *
 * 与 backend/app/services/auth_service.py 一致：
 * 注册成功 201 并直接返回令牌；学号重复 409；参数不合法 422；
 * 口令错误 401（中文 message）、账户停用 403、登录成功只返回 access_token。
 */
import { http } from 'msw'

import type { LoginRequest, RegisterRequest, TokenResponse } from '@/types'

import {
  createSession,
  findUserByStudentNo,
  getDb,
  nextId,
  publicUser,
  type UserRecord,
} from '../db'
import { abort, json, readBody, requireUser, safe } from '../http'
import { formatDateTime, serverNow } from '../time'

export const authHandlers = [
  http.post('/api/v1/auth/register', ({ request }) =>
    safe(async () => {
      const payload = await readBody<Partial<RegisterRequest>>(request)

      const name = (typeof payload.name === 'string' ? payload.name : '').trim()
      const studentNo = (
        typeof payload.student_no === 'string' ? payload.student_no : ''
      ).trim()
      const password = typeof payload.password === 'string' ? payload.password : ''
      const rawContact = payload.contact
      if (rawContact !== undefined && rawContact !== null && typeof rawContact !== 'string') {
        abort(422, 'VALIDATION_ERROR', '联系方式必须是字符串')
      }
      const contact = (rawContact ?? '').trim()

      if (name.length < 2 || name.length > 50) {
        abort(422, 'VALIDATION_ERROR', '姓名长度为 2-50 个字符')
      }
      if (!/^[A-Za-z0-9_-]{4,32}$/.test(studentNo)) {
        abort(422, 'VALIDATION_ERROR', '学号/工号为 4-32 位字母、数字、下划线或短横线')
      }
      if (password.length < 8 || password.length > 64 || password.trim() === '') {
        abort(422, 'VALIDATION_ERROR', '密码长度为 8-64 个字符且不能全为空白')
      }
      if (contact.length > 100) {
        abort(422, 'VALIDATION_ERROR', '联系方式不能超过 100 个字符')
      }
      if (findUserByStudentNo(studentNo)) {
        abort(409, 'STUDENT_NO_TAKEN', '该学号/工号已注册，请直接登录')
      }

      const db = getDb()
      const user: UserRecord = {
        id: nextId(db.users),
        name,
        student_no: studentNo,
        password,
        role: '学生用户',
        account_status: '正常',
        violation_count: 0,
        contact: contact || null,
        created_at: formatDateTime(serverNow()),
      }
      db.users.push(user)

      const body: TokenResponse = {
        access_token: createSession(user.id),
        token_type: 'bearer',
      }
      return json(body, 201)
    }),
  ),

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
