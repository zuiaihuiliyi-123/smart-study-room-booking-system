import { describe, expect, it, vi, afterEach } from 'vitest'

import {
  formatApiDateTime,
  formatDate,
  formatDateTime,
  formatMonthDay,
  formatMonthDayTime,
  formatTimeSecond,
  isAfterToday,
  isBeforeToday,
  recentRange,
} from '@/utils/format'

afterEach(() => {
  vi.useRealTimers()
})

describe('formatDateTime', () => {
  it('格式化 SQLite 本地时间与 ISO 时间', () => {
    expect(formatDateTime('2026-11-12 10:05:00')).toBe('2026-11-12 10:05')
    expect(formatDateTime('2026-11-12T10:05:00')).toBe('2026-11-12 10:05')
  })

  it('空值与非法值返回占位符', () => {
    expect(formatDateTime(null)).toBe('-')
    expect(formatDateTime('')).toBe('-')
    expect(formatDateTime('not-a-date')).toBe('-')
  })

  it('支持 Date 与时间戳', () => {
    const date = new Date(2026, 10, 12, 9, 30)
    expect(formatDateTime(date)).toBe('2026-11-12 09:30')
    expect(formatDateTime(date.getTime())).toBe('2026-11-12 09:30')
  })
})

describe('其余日期格式化', () => {
  it('formatDate / formatTimeSecond / formatMonthDayTime / formatMonthDay', () => {
    expect(formatDate('2026-11-12 10:05:00')).toBe('2026-11-12')
    expect(formatTimeSecond('2026-11-12 10:05:09')).toBe('10:05:09')
    expect(formatMonthDayTime('2026-11-12 10:05:09')).toBe('11-12 10:05')
    expect(formatMonthDay('2026-11-12 10:05:09')).toBe('11-12')
  })

  it('formatApiDateTime 输出后端约定格式，非法值返回空串', () => {
    expect(formatApiDateTime('2026-11-12 10:05:09')).toBe('2026-11-12T10:05:09')
    expect(formatApiDateTime(null)).toBe('')
  })
})

describe('日期区间与边界', () => {
  it('recentRange 包含今天并向前取 N-1 天', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 10, 12, 10, 0, 0))
    expect(recentRange(7)).toEqual(['2026-11-06', '2026-11-12'])
    expect(recentRange(1)).toEqual(['2026-11-12', '2026-11-12'])
  })

  it('isAfterToday / isBeforeToday 按自然日边界判断', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date(2026, 10, 12, 10, 0, 0))
    expect(isAfterToday(new Date(2026, 10, 13, 0, 0))).toBe(true)
    expect(isAfterToday(new Date(2026, 10, 12, 23, 59))).toBe(false)
    expect(isBeforeToday(new Date(2026, 10, 11, 23, 59))).toBe(true)
    expect(isBeforeToday(new Date(2026, 10, 12, 0, 0))).toBe(false)
  })
})
