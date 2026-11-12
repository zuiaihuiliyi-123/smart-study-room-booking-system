import { describe, expect, it } from 'vitest'

import {
  COMPLAINT_SLA_WORKDAYS,
  complaintDeadline,
  complaintSla,
  workdaysBetween,
} from '@/utils/workday'

describe('complaintDeadline', () => {
  it('从创建时刻次日起算 3 个工作日，跳过周末', () => {
    // 2026-11-12 周四 → 周五(1) → 周一(2) → 周二(3)
    const deadline = complaintDeadline('2026-11-12 09:00:00')
    expect(deadline).not.toBeNull()
    expect(deadline?.getFullYear()).toBe(2026)
    expect(deadline?.getMonth()).toBe(10)
    expect(deadline?.getDate()).toBe(17)
    expect(deadline?.getHours()).toBe(23)
    expect(deadline?.getMinutes()).toBe(59)
  })

  it('创建时刻非法时返回 null', () => {
    expect(complaintDeadline(null)).toBeNull()
    expect(complaintDeadline('')).toBeNull()
    expect(complaintDeadline('not-a-date')).toBeNull()
  })
})

describe('workdaysBetween', () => {
  it('不把起始日计入，只数完整工作日', () => {
    const from = new Date(2026, 10, 12, 0, 0, 0)
    const to = new Date(2026, 10, 17, 23, 59, 0)
    expect(workdaysBetween(from, to)).toBe(COMPLAINT_SLA_WORKDAYS)
  })

  it('倒序或同一天返回 0', () => {
    const day = new Date(2026, 10, 12, 12, 0, 0)
    expect(workdaysBetween(day, day)).toBe(0)
    expect(workdaysBetween(new Date(2026, 10, 18), new Date(2026, 10, 12))).toBe(0)
  })
})

describe('complaintSla', () => {
  it('未超时时给出剩余工作日与截止文案', () => {
    const now = new Date(2026, 10, 13, 10, 0, 0)
    const sla = complaintSla('2026-11-12 09:00:00', now)
    expect(sla.overdue).toBe(false)
    expect(sla.overdueDays).toBe(0)
    expect(sla.deadlineText).toBe('2026-11-17 23:59')
    expect(sla.remainingWorkdays).toBeGreaterThan(0)
    expect(sla.note).toContain('3 个工作日')
  })

  it('超时时按自然日给出迟到量', () => {
    const now = new Date(2026, 10, 18, 10, 0, 0)
    const sla = complaintSla('2026-11-12 09:00:00', now)
    expect(sla.overdue).toBe(true)
    expect(sla.overdueDays).toBe(1)
    expect(sla.remainingWorkdays).toBe(0)
  })

  it('创建时间缺失时不给时限结论', () => {
    const sla = complaintSla(null, new Date())
    expect(sla.deadline).toBeNull()
    expect(sla.deadlineText).toBe('—')
    expect(sla.overdue).toBe(false)
  })
})
