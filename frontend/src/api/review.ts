import { http } from './request'
import type { PageResult, Review } from '@/types'

export const createReview = (data: {
  reservation_id: number
  score: number
  content?: string
}) => http.post<Review>('/reviews', data)

export const listMyReviews = (params: { page?: number; page_size?: number }) =>
    http.get<PageResult<Review>>('/reviews/me', params)
