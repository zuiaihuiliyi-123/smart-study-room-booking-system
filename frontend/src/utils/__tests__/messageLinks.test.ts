import { describe, expect, it } from 'vitest'

import type { StationMessage } from '@/types'
import {
  parseFocusId,
  relatedLabel,
  relatedObjectText,
  relatedRoute,
  relatedTarget,
} from '@/utils/messageLinks'

const message = (overrides: Partial<StationMessage> = {}): StationMessage => ({
  id: 1,
  type: '预约通知',
  title: '预约成功',
  content: '内容',
  related_type: '预约单',
  related_id: 12,
  is_read: false,
  created_at: '2026-11-12 10:00:00',
  ...overrides,
})

describe('relatedTarget / relatedLabel', () => {
  it('已知关联类型映射到学生端列表页', () => {
    expect(relatedTarget('预约单')?.route).toBe('/student/reservations')
    expect(relatedTarget('违约记录')?.label).toBe('我的违约')
    expect(relatedTarget('黑名单')?.route).toBe('/student/violations')
  })

  it('未知或空类型不跳转', () => {
    expect(relatedTarget(null)).toBeNull()
    expect(relatedTarget('未知类型')).toBeNull()
    expect(relatedLabel('未知类型')).toBe('查看详情')
    expect(relatedLabel(null)).toBe('仅通知')
  })
})

describe('relatedObjectText', () => {
  it('有 id 时带编号，没有 id 时只显示类型', () => {
    expect(relatedObjectText(message())).toBe('预约单 #12')
    expect(relatedObjectText(message({ related_id: null }))).toBe('预约单')
    expect(relatedObjectText(message({ related_type: null, related_id: null }))).toBe('')
  })
})

describe('relatedRoute', () => {
  it('预约单等带 focus 参数，高亮目标记录', () => {
    expect(relatedRoute(message())).toBe('/student/reservations?focus=12')
    expect(relatedRoute(message({ related_type: '投诉', related_id: 3 }))).toBe(
      '/student/complaints?focus=3',
    )
  })

  it('黑名单没有学生端记录页，只跳违约页不带 focus', () => {
    expect(relatedRoute(message({ related_type: '黑名单', related_id: 9 }))).toBe(
      '/student/violations',
    )
  })

  it('无关联对象或未知类型返回 null', () => {
    expect(relatedRoute(message({ related_type: null, related_id: null }))).toBeNull()
    expect(relatedRoute(message({ related_type: '未知', related_id: 1 }))).toBeNull()
  })
})

describe('parseFocusId', () => {
  it('接受正整数与字符串数组首项', () => {
    expect(parseFocusId('12')).toBe(12)
    expect(parseFocusId(['7', '8'])).toBe(7)
  })

  it('非法值返回 null', () => {
    expect(parseFocusId(undefined)).toBeNull()
    expect(parseFocusId('')).toBeNull()
    expect(parseFocusId('0')).toBeNull()
    expect(parseFocusId('-3')).toBeNull()
    expect(parseFocusId('abc')).toBeNull()
  })
})
