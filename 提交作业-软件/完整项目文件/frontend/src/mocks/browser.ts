/**
 * MSW 浏览器端入口：由 main.ts 在 `import.meta.env.DEV && VITE_USE_MOCK === 'true'` 时动态导入。
 *
 * 另外暴露 `window.__ssrMock` 作为**仅开发期**的演示控制台（业务代码完全不需要感知）：
 * - `__ssrMock.setTimeOffset(20)` 把「服务器时间」后移 20 分钟，用于演示签到窗口；
 * - `__ssrMock.armConflict()` 让下一次创建预约返回 409（并发冲突路径）；
 * - `__ssrMock.reset()` 恢复种子数据（页面刷新同样会恢复）；
 * - `__ssrMock.dump()` 打印数据规模与各状态计数，便于自检。
 */
import { setupWorker } from 'msw/browser'

import { armConflict, getDb, resetDb, type MockDb } from './db'
import { handlers } from './handlers'
import { formatDateTime, getTimeOffsetMinutes, serverNow, setTimeOffsetMinutes } from './time'

export const worker = setupWorker(...handlers)

export interface MockControl {
  /** 服务器时间偏移（分钟，可为负） */
  setTimeOffset(minutes: number): number
  getTimeOffset(): number
  reset(): void
  /** 让接下来 N 次「创建预约」返回 409，用于演示并发冲突 */
  armConflict(times?: number): number
  dump(): Record<string, number | string>
  help(): void
}

function summarize(db: MockDb): Record<string, number | string> {
  const summary: Record<string, number | string> = {
    server_time: formatDateTime(serverNow()),
    time_offset_minutes: getTimeOffsetMinutes(),
    rooms: db.rooms.length,
    areas: db.areas.length,
    seats: db.seats.length,
    seats_available: db.seats.filter((seat) => seat.status === '可用').length,
    users: db.users.length,
    users_restricted: db.users.filter((user) => user.account_status === '受限').length,
    reservations: db.reservations.length,
    violations: db.violations.length,
    complaints: db.complaints.length,
    reviews: db.reviews.length,
    messages: db.messages.length,
    messages_unread: db.messages.filter((item) => !item.is_read).length,
    blacklist: db.blacklist.length,
  }
  const statuses = ['待使用', '使用中', '已完成', '已取消', '已违约']
  for (const status of statuses) {
    summary[`reservations_${status}`] = db.reservations.filter(
      (item) => item.status === status,
    ).length
  }
  return summary
}

function buildControl(): MockControl {
  return {
    setTimeOffset(minutes: number): number {
      const applied = setTimeOffsetMinutes(minutes)
      console.info(`[mock] 服务器时间偏移已设为 ${applied} 分钟，当前 ${formatDateTime(serverNow())}`)
      return applied
    },
    getTimeOffset: getTimeOffsetMinutes,
    reset(): void {
      resetDb()
      console.info('[mock] 内存数据已重置为种子状态')
    },
    armConflict(times = 1): number {
      const armed = armConflict(times)
      console.info(`[mock] 接下来 ${armed} 次创建预约将返回 409（并发冲突）`)
      return armed
    },
    dump: () => summarize(getDb()),
    help(): void {
      console.info(
        [
          '[mock] 开发期演示控制台：',
          '  __ssrMock.dump()                    查看数据规模与各状态计数',
          '  __ssrMock.setTimeOffset(20)         服务器时间后移 20 分钟（签到窗口演示）',
          '  __ssrMock.setTimeOffset(0)          恢复真实时间',
          '  __ssrMock.armConflict()             下一次创建预约返回 409',
          '  __ssrMock.reset()                   恢复种子数据',
          '演示账号：student / student123（学生）、admin / admin123（自习室管理员）',
          '受限账户：3200104523 / student123（累计违约 3 次，创建预约会被拒绝）',
        ].join('\n'),
      )
    },
  }
}

declare global {
  interface Window {
    __ssrMock?: MockControl
  }
}

window.__ssrMock = buildControl()
console.info('[mock] MSW 已启用，输入 __ssrMock.help() 查看演示指令')
