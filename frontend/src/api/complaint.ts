import { http } from './request'
import type { Complaint, PageResult } from '@/types'

/** 管理端投诉队列查询（FR-043）：状态 / 对象类型 / 提交时间区间。 */
export interface ComplaintQuery {
  status?: string
  target_type?: string
  /** 提交时间区间（含端点），形如 `2026-10-01` */
  created_from?: string
  created_to?: string
  page?: number
  page_size?: number
}

export const createComplaint = (data: {
  target_type: string
  target_id: number
  content: string
}) => http.post<Complaint>('/complaints', data)

export const listMyComplaints = (params: { page?: number; page_size?: number }) =>
    http.get<PageResult<Complaint>>('/complaints/me', params)

  export const listAllComplaints = (params: ComplaintQuery) =>
      http.get<PageResult<Complaint>>('/complaints', params)

    /** FR-043：处理投诉。`handle_note` 为处理说明，必填（后端 min_length=1）。 */
    export const handleComplaint = (
      complaintId: number,
      data: { status: string; handle_note: string },
    ) => http.patch<Complaint>(`/complaints/${complaintId}`, data)

    /** ST-063：投诉人确认处理结果，将「已处理」投诉关闭。 */
    export const confirmComplaint = (complaintId: number) =>
      http.post<Complaint>(`/complaints/${complaintId}/confirm`)
