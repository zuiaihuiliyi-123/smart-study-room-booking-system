import { http } from './request'
import type { PageResult, Review } from '@/types'

/** 管理端评价列表查询（FR-041）：评分 / 提交日期区间 / 分页。 */
export interface ReviewQuery {
  score?: number
  /** 提交日期起（含），形如 `2026-11-01` */
  created_from?: string
  /** 提交日期止（含） */
  created_to?: string
  page?: number
  page_size?: number
}

export const createReview = (data: {
  reservation_id: number
  score: number
  content?: string
}) => http.post<Review>('/reviews', data)

export const listMyReviews = (params: { page?: number; page_size?: number }) =>
  http.get<PageResult<Review>>('/reviews/me', params)

/** 管理端评价列表：只读，支持评分与提交日期筛选。 */
export const listAllReviews = (params: ReviewQuery) =>
  http.get<PageResult<Review>>('/reviews', params)
