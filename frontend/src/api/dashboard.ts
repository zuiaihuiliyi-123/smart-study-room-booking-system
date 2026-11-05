import { http, type RequestOptions } from './request'
import type { ChartItem, SeatUsageSlotRow, StatOverview, TrendPoint } from '@/types'

/**
 * 看板查询参数（IR-004 输入：自习室 + 统计周期起止自然日）。
 * `room_id` 缺省表示「全部自习室」（管理员授权范围内的全部，BR-018）。
 */
export interface DashboardQuery {
  start_date: string
  end_date: string
  room_id?: number
}

/**
 * FR-052：5 项概览数值。
 *
 * 注意 ⑤ 受限账户数：账户不归属自习室，因此该项始终是**全局口径**，
 * 传 `room_id` 时也不会被范围收窄（页面在卡片注脚里写明）。
 */
export const getOverview = (params: DashboardQuery, options?: RequestOptions) =>
    http.get<StatOverview>('/dashboard/overview', params, options)

  /**
   * 图 1：各自习室各时段座位占用率（`group_by=slot`）。
   *
   * 与 FR-050 原文口径（「各座位已使用时段数」）同源，只是分组维度从座位换成时段桶：
   * 逐座位口径仍可通过 `getSeatUsage` 取得，本轮看板按任务要求展示占用率视图。
   */
  export const getSeatUsageBySlot = (params: DashboardQuery, options?: RequestOptions) =>
      http.get<SeatUsageSlotRow[]>(
      '/dashboard/seat-usage',
      { ...params, group_by: 'slot' },
      options,
    )

    /** FR-050 原文口径：各座位在统计周期内的已使用时段数（当前看板未使用，保留作口径对照）。 */
    export const getSeatUsage = (params: DashboardQuery, options?: RequestOptions) =>
        http.get<ChartItem[]>('/dashboard/seat-usage', params, options)

      /** FR-051：按自然日的每日有效预约数与违约数（近 7 天趋势）。 */
      export const getTrend = (params: DashboardQuery, options?: RequestOptions) =>
          http.get<TrendPoint[]>('/dashboard/trend', params, options)
