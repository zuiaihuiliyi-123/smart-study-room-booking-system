export type Role = '学生用户' | '自习室管理员' | '教师用户' | '系统管理员'

export interface CurrentUser {
  id: number
  name: string
  student_no: string
  role: Role
  account_status: string
  violation_count: number
  contact: string | null
}

export interface LoginRequest {
  student_no: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface Room {
  id: number
  name: string
  location: string
  open_time: string
  close_time: string
  capacity: number
  enabled: boolean
}

export interface Area {
  id: number
  room_id: number
  name: string
}

export interface Seat {
  id: number
  room_id: number
  area_id: number | null
  seat_no: string
  seat_type: string
  has_power: boolean
  status: '可用' | '维修中' | '停用'
}

export interface Reservation {
  id: number
  user_id: number
  seat_id: number
  reserve_date: string
  start_time: string
  end_time: string
  status: '待使用' | '使用中' | '已完成' | '已取消' | '已违约'
  check_in_time: string | null
  check_out_time: string | null
  cancel_time: string | null
  cancel_reason: string | null
  created_at: string
}

export interface Violation {
  id: number
  user_id: number
  reservation_id: number
  type: '自动违约' | '手动违约'
  reason: string
  operator_id: number | null
  created_at: string
}

export interface Review {
  id: number
  user_id: number
  reservation_id: number
  score: number
  content: string | null
  created_at: string
}

export interface Complaint {
  id: number
  user_id: number
  target_type: string
  target_id: number
  content: string
  status: '待处理' | '处理中' | '已处理' | '已驳回' | '已关闭'
  handler_id: number | null
  handle_note: string | null
  handled_at: string | null
  created_at: string
}

export interface BlacklistEntry {
  id: number
  user_id: number
  reason: string
  mode: '自动' | '手动'
  start_at: string
  expire_at: string | null
  released_at: string | null
  operator_id: number | null
}

export interface StatOverview {
  seat_total: number
  in_use: number
  today_reservations: number
  today_violations: number
  restricted_accounts: number
}

export interface ChartItem {
  name: string
  value: number
}

export interface TrendPoint {
  date: string
  reservations: number
  violations: number
}

export interface StationMessage {
  id: number
  type: string
  title: string
  content: string
  related_type: string | null
  related_id: number | null
  is_read: boolean
  created_at: string
}
