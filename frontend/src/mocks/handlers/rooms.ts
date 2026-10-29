/**
 * 自习室 mock：GET/POST /rooms、PATCH /rooms/{id}、GET/POST /rooms/{id}/areas、
 * BR-019/BR-022 的临时关闭两步接口（close-preview → close）。
 *
 * 对齐 backend/app/api/v1/rooms.py：GET 不需要鉴权，写操作仅管理员。
 * 其中 `PATCH /rooms/{id}`、`GET /rooms/{id}/areas`、`POST /rooms/{id}/close`（含 preview）
 * 在**后端尚未实现**——路径与请求体按前端所需口径先在前端固化，属待补接口，
 * 已在交付说明的接口缺口清单中登记；后端补齐后本文件即为同构参照。
 */
import { http } from 'msw'

import type { Area, ConflictPreview, Room, RoomCloseResult } from '@/types'

import { getDb, nextId, publicReservation, pushMessage, type MockDb, type ReservationRecord } from '../db'
import { abort, json, param, readBody, requireAdmin, safe } from '../http'
import { isEffective } from '../rules'
import { formatDateTime, serverNow } from '../time'

const TIME_PATTERN = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/

  function parseMoment(value: string): number | null {
  const matched = TIME_PATTERN.exec(value.trim())
  if (!matched) return null
  const parsed = new Date(
    Number(matched[1]),
    Number(matched[2]) - 1,
    Number(matched[3]),
    Number(matched[4]),
    Number(matched[5]),
  )
  return Number.isNaN(parsed.getTime()) ? null : parsed.getTime()
}

function slotStart(record: ReservationRecord): number {
  return parseMoment(`${record.reserve_date}T${record.start_time}`) ?? 0
}

function slotEnd(record: ReservationRecord): number {
  return parseMoment(`${record.reserve_date}T${record.end_time}`) ?? 0
  }

  interface Window {
    fromMs: number
    toMs: number
  }

  interface Affected {
    seats: MockDb['seats']
    reservations: ReservationRecord[]
  }

  /** 受影响范围 = 窗口与「有效预约」的占用区间重叠（左闭右开），范围限自习室 / 分区。 */
  function collectAffected(
    db: MockDb,
    roomId: number,
    areaId: number | null,
    window: Window,
  ): Affected {
    const seats = db.seats.filter(
      (seat) => seat.room_id === roomId && (areaId === null || seat.area_id === areaId),
    )
    const seatIds = new Set(seats.map((seat) => seat.id))
    const reservations = db.reservations.filter(
      (record) =>
          seatIds.has(record.seat_id) &&
          isEffective(record.status) &&
          slotStart(record) < window.toMs &&
          window.fromMs < slotEnd(record),
      )
      return { seats, reservations }
    }

    function readWindow(query: URLSearchParams): Window | null {
      const fromMs = parseMoment(query.get('start_at') ?? '')
      const toMs = parseMoment(query.get('end_at') ?? '')
      if (fromMs === null || toMs === null || fromMs >= toMs) return null
      return { fromMs, toMs }
    }

    export const roomHandlers = [
      http.get('/api/v1/rooms', () => safe(() => json(getDb().rooms))),

      http.post('/api/v1/rooms', ({ request }) =>
          safe(async () => {
          requireAdmin(request)
          const db = getDb()
          const payload = await readBody<Partial<Room>>(request)
          const name = (payload.name ?? '').trim()
          const location = (payload.location ?? '').trim()
          if (name === '' || location === '') {
            return abort(400, 'INVALID_ARGUMENT', '自习室名称与位置不能为空')
          }
          if (db.rooms.some((item) => item.name === name)) {
            return abort(400, 'ROOM_EXISTS', `自习室「${name}」已存在`)
      }
      const room: Room = {
        id: nextId(db.rooms),
        name,
        location,
        open_time: payload.open_time ?? '08:00',
        close_time: payload.close_time ?? '22:00',
        capacity: typeof payload.capacity === 'number' ? payload.capacity : 0,
        enabled: true,
      }
      db.rooms.push(room)
      return json(room, 201)
    }),
  ),

  /** FR-001：修改自习室属性（名称 / 位置 / 开放时间 / 容量 / 启用状态）。 */
  http.patch('/api/v1/rooms/:roomId', ({ request, params }) =>
    safe(async () => {
      requireAdmin(request)
      const db = getDb()
      const roomId = Number(param(params, 'roomId'))
      const room = db.rooms.find((item) => item.id === roomId)
      if (!room) return abort(404, 'ROOM_NOT_FOUND', '自习室不存在')

      const payload = await readBody<Partial<Room> & { reason?: string }>(request)
      if (payload.name !== undefined) {
        const name = payload.name.trim()
        if (name === '') return abort(400, 'INVALID_ARGUMENT', '自习室名称不能为空')
        if (db.rooms.some((item) => item.id !== roomId && item.name === name)) {
          return abort(400, 'ROOM_EXISTS', `自习室「${name}」已存在`)
            }
            room.name = name
          }
          if (payload.location !== undefined) {
            const location = payload.location.trim()
            if (location === '') return abort(400, 'INVALID_ARGUMENT', '位置不能为空')
            room.location = location
          }
          if (payload.open_time !== undefined) room.open_time = payload.open_time
          if (payload.close_time !== undefined) room.close_time = payload.close_time
          if (payload.capacity !== undefined) {
            const capacity = Number(payload.capacity)
            if (!Number.isInteger(capacity) || capacity < 0) {
              return abort(400, 'INVALID_ARGUMENT', '容量必须是不小于 0 的整数')
            }
            room.capacity = capacity
          }
          if (payload.enabled !== undefined) room.enabled = payload.enabled === true

          return json(room)
        }),
    ),

    /** FR-001：分区列表。后端尚无该只读路由（见文件头说明）。 */
    http.get('/api/v1/rooms/:roomId/areas', ({ params }) =>
        safe(() => {
        const roomId = Number(param(params, 'roomId'))
        if (!Number.isInteger(roomId)) {
          return abort(400, 'INVALID_ARGUMENT', '自习室参数不合法')
        }
        return json(getDb().areas.filter((item) => item.room_id === roomId))
      }),
  ),

  http.post('/api/v1/rooms/:roomId/areas', ({ request, params }) =>
      safe(async () => {
      requireAdmin(request)
      const db = getDb()
      const roomId = Number(param(params, 'roomId'))
      const room = db.rooms.find((item) => item.id === roomId)
      if (!room) return abort(404, 'ROOM_NOT_FOUND', '自习室不存在')

      const payload = await readBody<{ name?: string; reason?: string }>(request)
      const name = (payload.name ?? '').trim()
      if (name === '') return abort(400, 'INVALID_ARGUMENT', '区域名称不能为空')
      if (db.areas.some((item) => item.room_id === roomId && item.name === name)) {
        return abort(400, 'AREA_EXISTS', `自习室「${room.name}」下已存在区域「${name}」`)
      }

      const area: Area = { id: nextId(db.areas), room_id: roomId, name }
      db.areas.push(area)
      return json(area, 201)
    }),
  ),

  /** BR-022 第一步：查询受影响的冲突预约清单，只读、无任何数据变化。 */
  http.get('/api/v1/rooms/:roomId/close-preview', ({ request, params }) =>
    safe(() => {
      requireAdmin(request)
      const db = getDb()
      const roomId = Number(param(params, 'roomId'))
      const room = db.rooms.find((item) => item.id === roomId)
      if (!room) return abort(404, 'ROOM_NOT_FOUND', '自习室不存在')

      const query = new URL(request.url).searchParams
      const window = readWindow(query)
      if (window === null) {
        return abort(400, 'INVALID_ARGUMENT', '关闭窗口不合法：结束时间必须晚于开始时间')
      }
      const areaRaw = (query.get('area_id') ?? '').trim()
      const areaId = areaRaw === '' ? null : Number(areaRaw)
      if (areaId !== null && Number.isNaN(areaId)) {
        return abort(400, 'INVALID_ARGUMENT', '分区参数不合法')
      }

      const affected = collectAffected(db, roomId, areaId, window)
      const body: ConflictPreview = {
        seats: affected.seats,
        reservations: affected.reservations.map(publicReservation),
      }
      return json(body)
    }),
  ),

  /**
   * BR-022 第二步：执行关闭。
   * - 座位资源状态 →「停用」（座位状态只能由 FR-002 / FR-004 的管理员操作改变）；
   * - BR-019 默认口径：受影响预约**保留原状态**；仅当 `cancel_affected=true` 时批量取消，
           *   且不计违约、不补偿、不支持改约；
           * - `expected_reservation_ids` 与当前清单不一致时拒绝执行（防止「确认后清单已变化」）。
   */
  http.post('/api/v1/rooms/:roomId/close', ({ request, params }) =>
    safe(async () => {
      requireAdmin(request)
      const db = getDb()
      const roomId = Number(param(params, 'roomId'))
      const room = db.rooms.find((item) => item.id === roomId)
      if (!room) return abort(404, 'ROOM_NOT_FOUND', '自习室不存在')

      const payload = await readBody<{
        start_at?: string
        end_at?: string
        area_id?: number | null
        reason?: string
        cancel_affected?: boolean
        expected_reservation_ids?: number[]
      }>(request)

      const reason = (payload.reason ?? '').trim()
      if (reason === '') {
        return abort(400, 'INVALID_ARGUMENT', '临时关闭必须填写原因')
      }
      const fromMs = parseMoment(payload.start_at ?? '')
      const toMs = parseMoment(payload.end_at ?? '')
      if (fromMs === null || toMs === null || fromMs >= toMs) {
        return abort(400, 'INVALID_ARGUMENT', '关闭窗口不合法：结束时间必须晚于开始时间')
      }
      const areaId = typeof payload.area_id === 'number' ? payload.area_id : null
      const affected = collectAffected(db, roomId, areaId, { fromMs, toMs })

      const actualIds = affected.reservations.map((item) => item.id).sort((a, b) => a - b)
      const expected = Array.isArray(payload.expected_reservation_ids)
        ? [...payload.expected_reservation_ids].sort((a, b) => a - b)
        : null
      if (expected === null || expected.join(',') !== actualIds.join(',')) {
        return abort(
          409,
          'CONFLICT_LIST_CHANGED',
          '影响清单已变化，请重新查询受影响预约后再确认',
        )
      }

      const now = formatDateTime(serverNow())
      for (const seat of affected.seats) {
        seat.status = '停用'
      }

      let cancelled = 0
      if (payload.cancel_affected === true) {
        for (const record of affected.reservations) {
          record.status = '已取消'
          record.cancel_time = now
          record.cancel_reason = `场地临时关闭：${reason}`
          record.updated_at = now
          cancelled += 1
          pushMessage(record.user_id, {
            type: '预约通知',
            title: '预约已被取消（场地临时关闭）',
            content: `因${room.name}场地临时关闭（原因：${reason}），你 ${record.reserve_date} ${record.start_time.slice(0, 5)}–${record.end_time.slice(0, 5)} 的预约已被取消，该情形不计违约。`,
            relatedType: '预约单',
            relatedId: record.id,
          })
        }
      } else {
        for (const record of affected.reservations) {
          pushMessage(record.user_id, {
            type: '系统通知',
            title: '所选座位临时关闭',
            content: `${room.name} ${record.reserve_date} ${record.start_time.slice(0, 5)}–${record.end_time.slice(0, 5)} 的场地临时关闭（原因：${reason}），你的预约暂时保留，请留意后续通知或联系管理员。`,
            relatedType: '预约单',
            relatedId: record.id,
          })
      }
    }

    const body: RoomCloseResult = {
      closed_seats: affected.seats.length,
      cancelled,
      kept: affected.reservations.length - cancelled,
    }
    return json(body)
  }),
),
]
