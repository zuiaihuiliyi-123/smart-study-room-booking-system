/**
 * 投诉对象的取值口径与状态推进文案（FR-042 / FR-043）。
 *
 * 取值依据：SRS 第 4.x 节 FR-042「投诉对象类型共 4 类——座位、自习室、预约单、被投诉用户」
 * 与 Q-008 定稿；状态机为 待处理 → 处理中 → 已处理 → 已关闭，或 待处理 → 已驳回
 * （ST-060～ST-063），处理时限 BR-014 = 3 个工作日。
 */
import type { Complaint } from '@/types'

export const TARGET_TYPES = ['座位', '自习室', '预约单', '用户'] as const

export type TargetType = (typeof TARGET_TYPES)[number]

export const TARGET_HINTS: Record<TargetType, string> = {
  座位: '按座位选择；候选项来自 GET /rooms 与 GET /rooms/{room_id}/seats',
  自习室: '按自习室选择',
  预约单: '从本人名下的预约单中选择',
  用户: '填写对方的用户编号；系统不采集也不展示他人姓名与学号',
}

export interface TimelineStep {
  title: string
  /** 空串表示该节点的时刻后端未记录，界面不编造时间 */
  time: string
  note: string
  type: 'primary' | 'success' | 'warning' | 'danger' | 'info'
}

/** 单个投诉的进度节点：提交 → 处理中 → 已处理 / 已驳回 / 已关闭。 */
export function complaintTimeline(item: Complaint): TimelineStep[] {
  const steps: TimelineStep[] = [
    {
      title: '提交',
      time: item.created_at,
      note: `投诉对象：${item.target_type} #${item.target_id}`,
      type: 'primary',
    },
  ]

  if (item.status === '待处理') {
    steps.push({
      title: '待处理',
      time: '',
      note: '管理员尚未受理：处理时限为自提交起 3 个工作日',
      type: 'warning',
    })
  return steps
}

if (item.status === '处理中') {
  steps.push({
    title: '处理中',
    time: item.handled_at ?? '',
    note: item.handle_note ?? '管理员已受理，正在核实',
    type: 'primary',
  })
return steps
}

steps.push({
  title: '处理中',
  time: '',
  note: '管理员已受理（受理时刻后端未单独记录）',
  type: 'info',
})
steps.push({
  title: item.status,
  time: item.handled_at ?? '',
  note: item.handle_note ?? '无处理说明',
  type: item.status === '已处理' ? 'success' : item.status === '已驳回' ? 'danger' : 'info',
})
return steps
}
