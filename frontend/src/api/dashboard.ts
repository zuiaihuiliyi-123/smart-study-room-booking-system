import { http } from './request'
import type { ChartItem, StatOverview, TrendPoint } from '@/types'

export const getOverview = () => http.get<StatOverview>('/dashboard/overview')

export const getSeatUsage = (params: { start_date: string; end_date: string }) =>
  http.get<ChartItem[]>('/dashboard/seat-usage', params)

export const getTrend = (params: { start_date: string; end_date: string }) =>
  http.get<TrendPoint[]>('/dashboard/trend', params)
