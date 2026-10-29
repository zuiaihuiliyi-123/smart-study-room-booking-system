/**
 * 预约 mock：创建、本人/全部列表、可预约座位、取消、强制取消。
 * 路径与请求体对齐 src/api/reservation.ts 与 backend/app/api/v1/reservations.py。
 *
 * 创建流程：幂等键去重（BR-021）→ 并发冲突 409（NFR-003）→ C1～C6 判定（FR-012）→ 落库 + 站内通知。
 */
import { http } from 'msw'

import { consumeConflict, findReservation, getDb, nextId, noteAttempt, publicReservation, pushMessage, seatLabel, type MockDb, type ReservationRecord } from '../db'
import { abort, fromError, intParam, json, pageOf, param, readBody, requireAdmin, requireUser, safe, strParam } from '../http'
import { availableSeats, parseSlot, validateBooking, validateCancel, validateForceCancel, validateSeatQuery } from '../rules'
import { formatDate, formatDateTime, minutesToTime, serverNow } from '../time'

/** 列表统一按「日期倒序 + 开始时间倒序」。 */
function sortForList(records: readonly ReservationRecord[]): ReservationRecord[] {
  return [...records].sort((left, right) => {
    if (left.reserve_date !== right.reserve_date) {
      return left.reserve_date < right.reserve_date ? 1 : -1
    }
    if (left.start_time !== right.start_time) {
      return left.start_time < right.start_time ? 1 : -1
    }
    return right.id - left.id
  })
}

/**
 * 管理端列表的筛选口径（FR-030 管理端口径 / FR-031 / FR-032）：
 * 状态、预约日期区间、自习室、座位、学号。
 * 后端 `GET /reservations` 目前只有 `status / page / page_size`，其余为待补参数
 * （见交付说明的接口缺口清单）；mock 先按最终口径实现，便于界面联调。
 */
function listResponse(
  db: MockDb,
  records: readonly ReservationRecord[],
  query: URLSearchParams,
): Response {
  const status = strParam(query, 'status')
  const dateFrom = strParam(query, 'reserve_date_from')
  const dateTo = strParam(query, 'reserve_date_to')
  const studentNo = strParam(query, 'student_no')
  const roomId = intParam(query, 'room_id', Number.NaN)
  const seatId = intParam(query, 'seat_id', Number.NaN)

  const roomSeatIds = Number.isFinite(roomId)
    ? new Set(db.seats.filter((seat) => seat.room_id === roomId).map((seat) => seat.id))
    : null
  const userIds =
    studentNo === ''
    ? null
    : new Set(db.users.filter((user) => user.student_no === studentNo).map((user) => user.id))

  const filtered = records.filter((item) => {
    if (status !== '' && item.status !== status) return false
    if (dateFrom !== '' && item.reserve_date < dateFrom) return false
    if (dateTo !== '' && item.reserve_date > dateTo) return false
    if (roomSeatIds !== null && !roomSeatIds.has(item.seat_id)) return false
    if (Number.isFinite(seatId) && item.seat_id !== seatId) return false
    if (userIds !== null && !userIds.has(item.user_id)) return false
    return true
  })
return json(pageOf(sortForList(filtered).map(publicReservation), query))
}

export const reservationHandlers = [
  http.get('/api/v1/reservations/me', ({ request }) =>
      safe(() => {
      const user = requireUser(request)
      const query = new URL(request.url).searchParams
      const mine = getDb().reservations.filter((item) => item.user_id === user.id)
      return listResponse(getDb(), mine, query)
    }),
),

http.get('/api/v1/reservations/available-seats', ({ request }) =>
    safe(() => {
    const user = requireUser(request)
    const query = new URL(request.url).searchParams
    const input = {
      room_id: intParam(query, 'room_id', Number.NaN),
      reserve_date: strParam(query, 'reserve_date'),
      start_time: strParam(query, 'start_time'),
      end_time: strParam(query, 'end_time'),
    }
    const plan = validateSeatQuery(getDb(), user, input)
    if (!plan.ok) return fromError(plan.error)
    return json(availableSeats(getDb(), user, plan.value))
  }),
),

http.get('/api/v1/reservations', ({ request }) =>
    safe(() => {
    requireAdmin(request)
    const query = new URL(request.url).searchParams
    const db = getDb()
    return listResponse(db, db.reservations, query)
  }),
),

http.post('/api/v1/reservations', ({ request }) =>
    safe(async () => {
    const user = requireUser(request)
    const db = getDb()
    const payload = await readBody<{
      seat_id?: number
      reserve_date?: string
      start_time?: string
      end_time?: string
      idempotency_key?: string
    }>(request)

    const key = (payload.idempotency_key ?? '').trim()
    if (key.length < 8 || key.length > 64) {
      return abort(400, 'INVALID_ARGUMENT', '幂等键长度须为 8～64 位')
    }

    // ① 幂等：同一用户 + 同一幂等键返回同一张预约单，不新增记录（BR-021）
    const existing = db.reservations.find(
      (item) => item.user_id === user.id && item.idempotency_key === key,
    )
    if (existing) return json(publicReservation(existing))

    const seatId = Number(payload.seat_id)
    const input = {
      seat_id: seatId,
      reserve_date: payload.reserve_date ?? '',
      start_time: payload.start_time ?? '',
      end_time: payload.end_time ?? '',
    }

    const parsed = parseSlot(input)
    if (!parsed.ok) return fromError(parsed.error)

    // ② 并发冲突：5 秒内同一用户对同一座位同一时段的重复提交返回 409（NFR-003「恰好一条成功」）
    if (consumeConflict(user.id, seatId, input.reserve_date, parsed.value.start, parsed.value.end)) {
      return abort(
        409,
        'CONCURRENT_CONFLICT',
        '该时段已被预约，请重新选择',
        { rule: 'NFR-003' },
      )
    }

    // ③ C1～C6 完整判定
    const plan = validateBooking(db, user, input)
    if (!plan.ok) return fromError(plan.error)
    const { seat, room, slot } = plan.value

    const now = formatDateTime(serverNow())
    const record: ReservationRecord = {
      id: nextId(db.reservations),
      user_id: user.id,
      seat_id: seat.id,
      reserve_date: formatDate(slot.day),
      start_time: minutesToTime(slot.start),
      end_time: minutesToTime(slot.end),
      status: '待使用',
      check_in_time: null,
      check_out_time: null,
      cancel_time: null,
      cancel_reason: null,
      created_at: now,
      idempotency_key: key,
      updated_at: now,
    }
    db.reservations.push(record)
    noteAttempt(user.id, seat.id, record.reserve_date, slot.start, slot.end)

    pushMessage(user.id, {
      type: '预约通知',
      title: '预约成功',
      content: `你已预约 ${room.name} ${seat.seat_no}，${record.reserve_date} ${record.start_time.slice(0, 5)}–${record.end_time.slice(0, 5)}，请在开始前 15 分钟至开始后 15 分钟内签到。`,
        relatedType: '预约单',
        relatedId: record.id,
      })

      return json(publicReservation(record))
    }),
  ),

  http.post('/api/v1/reservations/:reservationId/cancel', ({ request, params }) =>
    safe(async () => {
      const user = requireUser(request)
      const record = findReservation(Number(param(params, 'reservationId')))
      if (!record) return abort(404, 'RESERVATION_NOT_FOUND', '预约单不存在')

      const payload = await readBody<{ reason?: string }>(request)
      const result = validateCancel(record, user)
      if (!result.ok) return fromError(result.error)

      const now = formatDateTime(serverNow())
      record.status = '已取消'
      record.cancel_time = now
      record.cancel_reason = (payload.reason ?? '').trim() || null
      record.updated_at = now

      pushMessage(user.id, {
        type: '预约通知',
        title: '预约已取消',
        content: `你已取消 ${seatLabel(record.seat_id)} ${record.reserve_date} ${record.start_time.slice(0, 5)}–${record.end_time.slice(0, 5)} 的预约。`,
      relatedType: '预约单',
      relatedId: record.id,
    })

  return json({ message: '预约已取消' })
}),
),

http.post('/api/v1/reservations/:reservationId/force-cancel', ({ request, params }) =>
    safe(async () => {
    requireAdmin(request)
    const record = findReservation(Number(param(params, 'reservationId')))
    if (!record) return abort(404, 'RESERVATION_NOT_FOUND', '预约单不存在')

    const payload = await readBody<{ reason?: string }>(request)
    const reason = (payload.reason ?? '').trim()
    if (reason === '') {
      return abort(400, 'INVALID_ARGUMENT', '强制取消必须填写原因')
    }
    const result = validateForceCancel(record)
    if (!result.ok) return fromError(result.error)

    const now = formatDateTime(serverNow())
    record.status = '已取消'
    record.cancel_time = now
    record.cancel_reason = `管理员强制取消：${reason}`
      record.updated_at = now

      pushMessage(record.user_id, {
        type: '预约通知',
        title: '预约已被管理员取消',
        content: `你 ${record.reserve_date} ${record.start_time.slice(0, 5)}–${record.end_time.slice(0, 5)} 的预约已被管理员取消（原因：${reason}），该情形不计违约。`,
    relatedType: '预约单',
    relatedId: record.id,
  })

return json({ message: '预约已强制取消' })
}),
),

/**
 * 管理端预约详情（FR-030 / FR-031 的「查看预约单摘要」）。
 * 放在数组末尾：`/reservations/me` 与 `/reservations/available-seats` 已先行注册，
 * 不会被本路由的 `:reservationId` 抢先匹配。后端尚无该只读路由。
 */
http.get('/api/v1/reservations/:reservationId', ({ request, params }) =>
    safe(() => {
    requireAdmin(request)
    const record = findReservation(Number(param(params, 'reservationId')))
    if (!record) return abort(404, 'RESERVATION_NOT_FOUND', '预约单不存在')
    return json(publicReservation(record))
  }),
),
]
