/**
 * 座位 mock：GET /rooms/{id}/seats、POST /seats、PATCH /seats/{id}/status、
 * PATCH /seats/status（批量）、GET /seats/occupancy（FR-003 / FR-031）、
 * GET /seats/conflicts（BR-019 冲突清单）。
 *
 * 座位只有资源状态（可用 / 维修中 / 停用）；「已预约 / 使用中」是按时段判定的
 * 派生结论，不写进 seat.status（AGENTS.md §4、BR-017）。因此占用接口返回的是
 * `{ seat, occupied, reservation }` 复合结构，而不是往座位里塞状态。
 *
 * 批量接口与占用 / 冲突接口在后端尚未实现（见交付说明的接口缺口清单）。
 */
import { http } from 'msw'

import type { Reservation, Seat, SeatOccupancy, SeatStatusBatchResult } from '@/types'

import { getDb, nextId, publicReservation, type MockDb, type ReservationRecord } from '../db'
import { abort, intParam, json, param, readBody, requireAdmin, safe, strParam } from '../http'
import { RULES, isEffective } from '../rules'
import { serverNow } from '../time'

const SEAT_STATUS: readonly Seat['status'][] = ['可用', '维修中', '停用']

const MOMENT = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/

  function parseMoment(value: string): number | null {
  const matched = MOMENT.exec(value.trim())
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

function startMs(record: ReservationRecord): number {
  return parseMoment(`${record.reserve_date}T${record.start_time}`) ?? 0
}

function endMs(record: ReservationRecord): number {
  return parseMoment(`${record.reserve_date}T${record.end_time}`) ?? 0
  }

  /** 某座位集合在窗口内的有效预约（左闭右开重叠）。 */
  function conflictsOf(
    db: MockDb,
    seatIds: ReadonlySet<number>,
    fromMs: number,
    toMs: number,
  ): ReservationRecord[] {
    return db.reservations.filter(
      (record) =>
          seatIds.has(record.seat_id) &&
          isEffective(record.status) &&
          startMs(record) < toMs &&
          fromMs < endMs(record),
      )
    }

    export const seatHandlers = [
      http.get('/api/v1/rooms/:roomId/seats', ({ params }) =>
          safe(() => {
          const roomId = Number(param(params, 'roomId'))
          if (!Number.isInteger(roomId)) {
            return abort(400, 'INVALID_ARGUMENT', '自习室参数不合法')
          }
          return json(getDb().seats.filter((seat) => seat.room_id === roomId))
        }),
    ),

    /**
     * FR-003 / FR-031：座位资源状态 + 该时段占用，两个维度分别返回。
     * 占用 = 存在与该时段重叠的有效预约（待使用 / 使用中）。
     */
    http.get('/api/v1/seats/occupancy', ({ request }) =>
        safe(() => {
        requireAdmin(request)
        const db = getDb()
        const query = new URL(request.url).searchParams
        const roomId = intParam(query, 'room_id', Number.NaN)
        if (!Number.isFinite(roomId)) {
          return abort(400, 'INVALID_ARGUMENT', '自习室参数不合法')
        }
        const day = strParam(query, 'reserve_date')
        const fromMs = parseMoment(`${day}T${strParam(query, 'start_time')}`)
      const toMs = parseMoment(`${day}T${strParam(query, 'end_time')}`)
          if (fromMs === null || toMs === null || fromMs >= toMs) {
            return abort(400, 'INVALID_ARGUMENT', '查询时段不合法：结束时间必须晚于开始时间')
          }

          const seats = db.seats.filter((seat) => seat.room_id === roomId)
          const seatIds = new Set(seats.map((seat) => seat.id))
          const conflicts = conflictsOf(db, seatIds, fromMs, toMs)

          const items: SeatOccupancy[] = seats.map((seat) => {
            const hit = conflicts.find((record) => record.seat_id === seat.id)
            return {
              seat,
              occupied: hit !== undefined,
              reservation: hit === undefined ? null : publicReservation(hit),
            }
          })
        return json(items)
      }),
  ),

  /** BR-019：列出与「所选座位 + 调整窗口」冲突的有效预约，仅供提示、不自动取消。 */
  http.get('/api/v1/seats/conflicts', ({ request }) =>
      safe(() => {
      requireAdmin(request)
      const db = getDb()
      const query = new URL(request.url).searchParams
      const ids = strParam(query, 'seat_ids')
        .split(',')
        .map((item) => Number(item.trim()))
        .filter((item) => Number.isInteger(item) && item > 0)
      if (ids.length === 0) {
        return abort(400, 'INVALID_ARGUMENT', '请至少选择一个座位')
      }
      const fromMs = parseMoment(strParam(query, 'start_at'))
      const toMs = parseMoment(strParam(query, 'end_at'))
      if (fromMs === null || toMs === null || fromMs >= toMs) {
        return abort(400, 'INVALID_ARGUMENT', '调整窗口不合法：结束时间必须晚于开始时间')
      }
      const records: Reservation[] = conflictsOf(db, new Set(ids), fromMs, toMs).map(
        publicReservation,
      )
      return json(records)
    }),
),

http.post('/api/v1/seats', ({ request }) =>
    safe(async () => {
    requireAdmin(request)
    const db = getDb()
    const payload = await readBody<Partial<Seat>>(request)
    const roomId = Number(payload.room_id)
    const seatNo = (payload.seat_no ?? '').trim()
    if (!Number.isInteger(roomId) || seatNo === '') {
      return abort(400, 'INVALID_ARGUMENT', '自习室与座位编号不能为空')
    }
    if (!db.rooms.some((item) => item.id === roomId)) {
      return abort(404, 'ROOM_NOT_FOUND', '自习室不存在')
    }
    if (db.seats.some((item) => item.room_id === roomId && item.seat_no === seatNo)) {
      return abort(400, 'SEAT_EXISTS', `该自习室已存在座位「${seatNo}」`)
      }
      const areaId = typeof payload.area_id === 'number' ? payload.area_id : null
      if (
        areaId !== null &&
        !db.areas.some((item) => item.id === areaId && item.room_id === roomId)
      ) {
        return abort(400, 'AREA_NOT_FOUND', '区域不存在或不属于该自习室')
      }

      const seat: Seat = {
        id: nextId(db.seats),
        room_id: roomId,
        area_id: areaId,
        seat_no: seatNo,
        seat_type: payload.seat_type ?? '普通',
        has_power: payload.has_power === true,
        status: '可用',
      }
      db.seats.push(seat)
      return json(seat, 201)
    }),
  ),

  /**
   * FR-004：单座位资源状态调整。
   * `reason` 为审计事由（NFR-009）——后端 `SeatStatusUpdate.reason` 可选，
         * 本版界面强制填写，理由登记在交付说明中。
         */
          http.patch('/api/v1/seats/:seatId/status', ({ request, params }) =>
            safe(async () => {
            requireAdmin(request)
            const db = getDb()
            const seatId = Number(param(params, 'seatId'))
            const seat = db.seats.find((item) => item.id === seatId)
            if (!seat) return abort(404, 'SEAT_NOT_FOUND', '座位不存在')

            const payload = await readBody<{ status?: Seat['status']; reason?: string }>(request)
            if (payload.status === undefined || !SEAT_STATUS.includes(payload.status)) {
              return abort(400, 'INVALID_ARGUMENT', '座位资源状态只能是「可用 / 维修中 / 停用」')
            }
            const reason = (payload.reason ?? '').trim()
            if (reason === '') {
              return abort(400, 'INVALID_ARGUMENT', '调整座位资源状态必须填写原因')
            }
            seat.status = payload.status
            return json(seat)
          }),
      ),

      /**
       * FR-004 + BR-022：批量调整资源状态。
       * 影响面 > 1 时前端已先列出冲突清单并二次确认；本接口按 BR-019 默认口径
       * **不取消任何预约**，只把冲突清单回给调用方用于持续提示。
       */
      http.patch('/api/v1/seats/status', ({ request }) =>
          safe(async () => {
          requireAdmin(request)
          const db = getDb()
          const payload = await readBody<{
            seat_ids?: number[]
            status?: Seat['status']
            reason?: string
          }>(request)

          const status = payload.status
          if (status === undefined || !SEAT_STATUS.includes(status)) {
            return abort(400, 'INVALID_ARGUMENT', '座位资源状态只能是「可用 / 维修中 / 停用」')
          }
          const reason = (payload.reason ?? '').trim()
          if (reason === '') {
            return abort(400, 'INVALID_ARGUMENT', '调整座位资源状态必须填写原因')
          }
          const ids = Array.isArray(payload.seat_ids) ? payload.seat_ids : []
          if (ids.length === 0) return abort(400, 'INVALID_ARGUMENT', '请至少选择一个座位')

          const targets = db.seats.filter((seat) => ids.includes(seat.id))
          if (targets.length !== ids.length) {
            return abort(404, 'SEAT_NOT_FOUND', '部分座位不存在，请刷新后重试')
          }

          for (const seat of targets) seat.status = status

          const now = serverNow()
          const conflicts =
            status === '可用'
            ? []
            : conflictsOf(
            db,
            new Set(targets.map((seat) => seat.id)),
            now.getTime(),
            now.getTime() + RULES.advanceDays * 86_400_000,
          ).map(publicReservation)

          const body: SeatStatusBatchResult = { updated: targets, conflicts }
          return json(body)
        }),
    ),
  ]
