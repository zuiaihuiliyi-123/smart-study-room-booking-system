import { http } from './request'
import type { Complaint, PageResult } from '@/types'

export const createComplaint = (data: {
  target_type: string
  target_id: number
  content: string
}) => http.post<Complaint>('/complaints', data)

export const listMyComplaints = (params: { page?: number; page_size?: number }) =>
  http.get<PageResult<Complaint>>('/complaints/me', params)

export const listAllComplaints = (params: { page?: number; page_size?: number }) =>
  http.get<PageResult<Complaint>>('/complaints', params)

export const handleComplaint = (
  complaintId: number,
  data: { status: string; handle_note: string },
) => http.patch<Complaint>(`/complaints/${complaintId}`, data)
