import { http } from './request'
import type { PageResult, StationMessage } from '@/types'

/** 消息类型筛选：不传表示全部。 */
export interface MessageQuery {
  page?: number
  page_size?: number
  /** 预约通知 / 违约通知 / 投诉反馈 / 系统通知 */
  type?: string
}

export const listMyMessages = (params: MessageQuery) =>
    http.get<PageResult<StationMessage>>('/messages/me', params)

/** 未读数量：与列表解耦，保证铃铛角标在任何分页下都与服务端一致。 */
export const getUnreadCount = () =>
    http.get<{ count: number }>('/messages/unread-count')

  export const markMessageRead = (messageId: number) =>
      http.post<StationMessage>(`/messages/${messageId}/read`)
