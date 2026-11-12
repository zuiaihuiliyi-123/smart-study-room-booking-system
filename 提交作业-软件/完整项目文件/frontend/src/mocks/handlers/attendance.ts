/**
 * 签到 / 签退 mock：POST /reservations/{id}/check-in、POST /reservations/{id}/check-out。
 * 与 backend/app/api/v1/attendance.py 一致（MessageResponse）。
 *
 * 签到窗口用「服务器时间」判定（BR-007）：[s-15min, s+15min)；
 * 重复签到幂等，不覆盖首次签到时间（FR-015）。
 */
import { http } from 'msw'

import { getDb } from '../db'
import { fromError, json, param, requireUser, safe } from '../http'
import { validateCheckIn, validateCheckOut } from '../rules'
import { formatDateTime, serverNow } from '../time'

export const attendanceHandlers = [
  http.post('/api/v1/reservations/:reservationId/check-in', ({ request, params }) =>
      safe(() => {
      const user = requireUser(request)
      const result = validateCheckIn(getDb(), user, Number(param(params, 'reservationId')))
      if (!result.ok) return fromError(result.error)

      const { record, repeat } = result.value
      if (!repeat) {
        record.status = '使用中'
        record.check_in_time = formatDateTime(serverNow())
        record.updated_at = record.check_in_time
      }
      return json({ message: repeat ? '该预约已签到，未重复记录' : '签到成功' })
    }),
),

http.post('/api/v1/reservations/:reservationId/check-out', ({ request, params }) =>
    safe(() => {
    const user = requireUser(request)
    const result = validateCheckOut(getDb(), user, Number(param(params, 'reservationId')))
    if (!result.ok) return fromError(result.error)

    const record = result.value
    record.status = '已完成'
    record.check_out_time = formatDateTime(serverNow())
    record.updated_at = record.check_out_time
    return json({ message: '签退成功' })
  }),
),
]
