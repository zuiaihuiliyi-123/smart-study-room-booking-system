export type Role = '学生用户' | '自习室管理员' | '教师用户' | '系统管理员'

export interface CurrentUser {
  id: number
  name: string
  student_no: string
  role: Role
  account_status: string
  violation_count: number
  contact: string | null
  /**
   * 受限账户的预计解除时间（BR-010）。
   * 后端 `UserRead` 目前**没有**这个字段，只有预约接口的 403 响应体带 `restrict_until`；
   * 这里预留为可选：后端补上后界面自动生效，缺失时页面明确标注「待后端提供接口」。
   */
  restrict_until?: string | null
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
  near_window: boolean
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
  release_reason: string | null
  operator_id: number | null
  /**
   * 手动解除的原因与解除人（ST-043：解除须记录原因）。
   * 后端 `BlacklistEntry` 目前没有这两个字段（解除原因只进 `audit_logs`），
   * 这里声明为可选：后端补齐后界面自动展示，缺失时显示「—」并标注待后端提供。
   */
  released_reason?: string | null
  released_by?: number | null
}

/**
 * 座位在某时段的占用派生结论（FR-003 / FR-031）。
 *
 * 注意：`occupied` 是**按时段实时计算**的结果，不是座位状态——AGENTS.md §4 明确
 * 「已预约 / 使用中」不得写进 `seat.status`，因此本结构把两个维度分别承载。
 */
export interface SeatOccupancy {
  seat: Seat
  occupied: boolean
  /** 该时段占用该座位的有效预约摘要；未被占用时为 null */
  reservation: Reservation | null
}

/** 场地临时关闭 / 批量状态调整前的影响清单（BR-019 / BR-022：先列清单，再二次确认）。 */
export interface ConflictPreview {
  /** 受影响范围内的座位 */
  seats: Seat[]
  /** 与关闭 / 调整窗口冲突的有效预约（待使用 / 使用中） */
  reservations: Reservation[]
}

/** 临时关闭的执行结果：关闭座位数、按管理员选择批量取消的预约数、按默认口径保留的预约数。 */
export interface RoomCloseResult {
  closed_seats: number
  cancelled: number
  kept: number
}

/** 批量调整座位资源状态的结果：已更新的座位 + 仅作提示、未被自动取消的冲突预约。 */
export interface SeatStatusBatchResult {
  updated: Seat[]
  conflicts: Reservation[]
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

/**
 * 图 1 的一行：某自习室在某时段桶内的座位占用率。
 *
 * 口径（本轮任务 + 原型 UC-14「各自习室各时段座位占用率」）：
 * `rate = occupied / capacity`，其中 capacity = 该自习室座位数 × 时段内 30 分钟块数 × 统计天数，
 * `occupied` 为被「待使用 / 使用中 / 已完成」预约覆盖的 30 分钟座位块数（已取消 / 已违约不计）。
 * 空自习室（capacity = 0）时 rate 为 0，由界面显示「无座位」，不用 0 值冒充「空闲」。
 */
export interface SeatUsageSlotRow {
  room_id: number
  room_name: string
  /** 时段桶，形如 `08:00-10:00`（左闭右开） */
  slot: string
  occupied: number
  capacity: number
  rate: number
}

/** 图 3 的一行：用户违约次数（由 `/violations` 明细聚合，前端计算） */
export interface ViolationTopEntry {
  user_id: number
  name: string
  student_no: string
  count: number
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
