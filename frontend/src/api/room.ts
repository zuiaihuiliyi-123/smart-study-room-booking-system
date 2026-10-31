import { http } from './request'
import type { Area, ConflictPreview, Room, RoomCloseResult } from '@/types'

export const listRooms = () => http.get<Room[]>('/rooms')

/** 新增自习室（FR-001）。`reason` 为审计事由（NFR-009），后端补齐后落到 `audit_logs`。 */
export const createRoom = (data: Partial<Room> & { reason?: string }) =>
  http.post<Room>('/rooms', data)

/** 修改自习室（FR-001）。`reason` 为审计事由（NFR-009），后端写入 `audit_logs`。 */
export const updateRoom = (roomId: number, data: Partial<Room> & { reason?: string }) =>
  http.patch<Room>(`/rooms/${roomId}`, data)

/** 新增分区（FR-001）。 */
export const createArea = (roomId: number, name: string, reason?: string) =>
  http.post<Area>(`/rooms/${roomId}/areas`, { name, reason })

/** 分区列表（FR-001 / 座位筛选需要）。 */
export const listAreas = (roomId: number) => http.get<Area[]>(`/rooms/${roomId}/areas`)

export interface RoomCloseQuery {
  /** 关闭窗口起点（含），形如 `2026-10-30T08:00` */
  start_at: string
  /** 关闭窗口终点（不含） */
  end_at: string
  /** 仅关闭某个分区时传入；缺省表示整个自习室 */
  area_id?: number
}

export interface RoomCloseRequest extends RoomCloseQuery {
  /** 关闭原因（BR-022 / NFR-009：批量操作须留痕，原因必填） */
  reason: string
  /** true = 管理员明确选择「同时批量取消」；false = 按 BR-019 默认保留冲突预约并持续提示 */
  cancel_affected: boolean
  /** 管理员二次确认时看到的影响清单；与实际不一致时服务端应拒绝执行（防止确认后清单变化） */
  expected_reservation_ids: number[]
}

/**
 * BR-022 第一步：查询受影响清单（不产生任何数据变化）。
 * 依据 FR-016：先列出受影响预约 → 二次确认 → 才执行；确认前不得自动取消用户预约（BR-019）。
 */
export const previewRoomClose = (roomId: number, params: RoomCloseQuery) =>
  http.get<ConflictPreview>(`/rooms/${roomId}/close-preview`, params)

/** BR-022 第二步：执行关闭（座位资源状态转「停用」；按选择决定是否批量取消受影响预约）。 */
export const closeRoom = (roomId: number, data: RoomCloseRequest) =>
  http.post<RoomCloseResult>(`/rooms/${roomId}/close`, data)
