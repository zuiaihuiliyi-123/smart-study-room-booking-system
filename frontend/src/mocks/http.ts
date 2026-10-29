/**
 * mock 层的 HTTP 辅助：响应构造、Bearer 校验、参数解析、异常兜底。
 *
 * 响应体形状与后端（FastAPI + pydantic）保持一致：
 * - 业务失败：`{ code, message }`（app/core/exceptions.py 的 BusinessError）
 * - 鉴权失败：`{ detail }`（HTTPException）
 * - 分页：`{ items, total, page, page_size }`
 */
import { HttpResponse, type JsonBodyType, type PathParams } from 'msw'

import type { PageResult } from '@/types'

import { findUser, paginate, resolveSession, type UserRecord } from './db'
import type { RuleError } from './rules'

export class MockHttpError extends Error {
  readonly response: Response

  constructor(response: Response) {
    super('mock-http-error')
    this.name = 'MockHttpError'
    this.response = response
  }
}

export function json<T extends JsonBodyType>(body: T, status = 200): Response {
  return HttpResponse.json(body, { status })
}

/** 业务异常响应（与 BusinessError 一致）。 */
export function problem(
  status: number,
  code: string,
  message: string,
  extra?: Record<string, unknown>,
): Response {
  return HttpResponse.json({ code, message, ...(extra ?? {}) }, { status })
}

/** FastAPI HTTPException 响应（仅 401/403 使用）。 */
export function detail(status: number, message: string, headers?: Record<string, string>): Response {
  return HttpResponse.json({ detail: message }, { status, headers })
}

/** 抛出即中断本次请求处理，由 safe() 转成响应。 */
export function abort(
  status: number,
  code: string,
  message: string,
  extra?: Record<string, unknown>,
): never {
  throw new MockHttpError(problem(status, code, message, extra))
}

export function fromError(error: RuleError): Response {
  return problem(error.status, error.code, error.message, error.extra)
}

export function unauthorized(): never {
  throw new MockHttpError(
    detail(401, '登录状态无效或已过期', { 'WWW-Authenticate': 'Bearer' }),
  )
}

export function forbidden(message = '无权限执行该操作'): never {
  throw new MockHttpError(detail(403, message))
}

/** 统一捕获：MockHttpError → 对应响应；其它异常 → 500，避免静默失败。 */
export async function safe(fn: () => Response | Promise<Response>): Promise<Response> {
  try {
    return await fn()
  } catch (error) {
    if (error instanceof MockHttpError) return error.response
    const message = error instanceof Error ? error.message : String(error)
    return problem(500, 'MOCK_ERROR', `mock 层异常：${message}`)
  }
}

export function requireUser(request: Request): UserRecord {
  const header = request.headers.get('Authorization') ?? ''
  const token = header.startsWith('Bearer ') ? header.slice(7).trim() : ''
  if (token === '') unauthorized()
  const session = resolveSession(token)
  if (!session) unauthorized()
  const user = findUser(session.user_id)
  if (!user || user.account_status === '停用') unauthorized()
  return user
}

export function requireAdmin(request: Request): UserRecord {
  const user = requireUser(request)
  if (user.role !== '自习室管理员' && user.role !== '系统管理员') forbidden()
  return user
}

export function param(params: PathParams, name: string): string {
  const value: string | readonly string[] | undefined = params[name]
  if (typeof value === 'string') return value
  if (value === undefined) return ''
  const first = value[0]
  return first === undefined ? '' : first
}

export function intParam(query: URLSearchParams, name: string, fallback: number): number {
  const raw = query.get(name)
  if (raw === null || raw.trim() === '') return fallback
  const parsed = Number.parseInt(raw, 10)
  return Number.isFinite(parsed) ? parsed : fallback
}

export function strParam(query: URLSearchParams, name: string): string {
  return (query.get(name) ?? '').trim()
}

export async function readBody<T>(request: Request): Promise<T> {
  try {
    const parsed: unknown = await request.json()
    if (parsed === null || typeof parsed !== 'object') {
      abort(400, 'INVALID_ARGUMENT', '请求体必须是 JSON 对象')
    }
    return parsed as T
  } catch (error) {
    if (error instanceof MockHttpError) throw error
    abort(400, 'INVALID_ARGUMENT', '请求体不是合法的 JSON')
  }
}

export function pageOf<T>(items: readonly T[], query: URLSearchParams): PageResult<T> {
  return paginate(items, intParam(query, 'page', 1), intParam(query, 'page_size', 20))
}
