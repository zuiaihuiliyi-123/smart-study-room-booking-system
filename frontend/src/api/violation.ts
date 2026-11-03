import { http } from './request'
import type { PageResult, Violation } from '@/types'

/** FR-032：管理员按「类型 / 时间区间 / 学号」查询全部违约记录。 */
export interface ViolationQuery {
  /** 违约类型：自动违约 / 手动违约 */
  type?: string
  /** 违约产生时间区间（含端点），形如 `2026-10-01` */
  created_from?: string
  created_to?: string
  /** 学号精确匹配 */
  student_no?: string
  page?: number
  page_size?: number
}

export const listMyViolations = (params: { page?: number; page_size?: number }) =>
    http.get<PageResult<Violation>>('/violations/me', params)

  export const listAllViolations = (params: ViolationQuery) =>
      http.get<PageResult<Violation>>('/violations', params)

    /** FR-023：管理员手动违约登记（仅「使用中」，必填原因，累加违约次数）。 */
    export const registerManualViolation = (data: {
      reservation_id: number
      reason: string
    }) => http.post<Violation>('/violations/manual', data)
