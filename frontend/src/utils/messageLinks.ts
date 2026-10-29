/**
 * 站内消息的关联对象 → 跳转目标（FR-060 / SCOPE-07）。
 *
 * 取值来源：mock 与服务端 `pushMessage(...)` 的全部调用点
 * （预约单 / 违约记录 / 投诉 / 黑名单，以及无关联对象的系统通知）。
 * 站内消息只能跳到**列表页**并在列表内高亮对应记录：路由没有详情页，
 * 也没有 `GET /reservations/{id}` 之类的单条查询接口。
 */
import type { StationMessage } from '@/types'

export interface RelatedTarget {
  /** 目标页面名称，用于「我的预约 →」这类文案 */
  label: string
  /** 路由路径 */
  route: string
}

const RELATED_TARGETS: Record<string, RelatedTarget> = {
  预约单: { label: '我的预约', route: '/student/reservations' },
  违约记录: { label: '我的违约', route: '/student/violations' },
  投诉: { label: '我的投诉', route: '/student/complaints' },
  // 账户限制通知（BR-009 / BR-010）没有独立页面，落到违约记录页的受限提示条
  黑名单: { label: '我的违约', route: '/student/violations' },
}

/** 关联对象的跳转目标；无关联对象或未知类型时返回 null（界面只提示、不跳转）。 */
export function relatedTarget(type: string | null): RelatedTarget | null {
  if (!type) return null
  return RELATED_TARGETS[type] ?? null
}

/** 列表项右侧的跳转文案：`我的预约 →` / `查看详情 →` / `仅通知`。 */
export function relatedLabel(type: string | null): string {
  if (!type) return '仅通知'
  return relatedTarget(type)?.label ?? '查看详情'
}

/** 关联对象摘要：`预约单 #123`；无关联对象时返回空串。 */
export function relatedObjectText(message: StationMessage): string {
  if (!message.related_type) return ''
  return message.related_id === null
    ? message.related_type
    : `${message.related_type} #${message.related_id}`
}

/**
 * 点击消息后的跳转地址：带 `focus` 查询参数，列表页据此高亮该条记录。
   * 只有存在关联对象与目标页面时才返回地址。
   */
    export function relatedRoute(message: StationMessage): string | null {
    const target = relatedTarget(message.related_type)
    if (!target) return null
    return message.related_id === null ? target.route : `${target.route}?focus=${message.related_id}`
}

/** 读取列表页的 `focus` 查询参数（用于高亮从消息跳转过来的记录）。 */
    export function parseFocusId(raw: unknown): number | null {
      const value = Array.isArray(raw) ? raw[0] : raw
      if (typeof value !== 'string' || value.trim() === '') return null
      const parsed = Number.parseInt(value, 10)
      return Number.isFinite(parsed) && parsed > 0 ? parsed : null
    }
