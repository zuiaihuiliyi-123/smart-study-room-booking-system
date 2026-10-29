/**
 * mock 处理集合：每个文件对应一个业务模块，路径与 src/api/*.ts 中的写法逐字一致。
 */
import { attendanceHandlers } from './attendance'
import { authHandlers } from './auth'
import { blacklistHandlers } from './blacklist'
import { complaintHandlers } from './complaints'
import { dashboardHandlers } from './dashboard'
import { messageHandlers } from './messages'
import { reservationHandlers } from './reservations'
import { reviewHandlers } from './reviews'
import { roomHandlers } from './rooms'
import { seatHandlers } from './seats'
import { userHandlers } from './users'
import { violationHandlers } from './violations'

export const handlers = [
  ...authHandlers,
  ...userHandlers,
  ...roomHandlers,
  ...seatHandlers,
  ...reservationHandlers,
  ...attendanceHandlers,
  ...violationHandlers,
  ...reviewHandlers,
  ...complaintHandlers,
  ...blacklistHandlers,
  ...dashboardHandlers,
  ...messageHandlers,
]
