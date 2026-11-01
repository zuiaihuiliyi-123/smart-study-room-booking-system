/**
 * 图表主题（AGENTS.md §3.8：图表色值集中在 `src/utils/chartTheme.ts`，视图里禁止散落十六进制）。
 *
 * 色值真值源是 `src/assets/styles/index.scss` 第 1 节的 SCSS 变量，本文件是它在 ECharts 侧的
 * 唯一投影。ECharts 的 option 只能吃具体色值字符串，无法直接写 `var(--ssr-primary)`，
 * 因此改色时**两处必须同步**（这条约定写在 index.scss 文件头）。
 */

/** 与 index.scss 第 1 节一一对应（Linear 暗色：近黑底 + 靛紫主色 + 白 10% 描边） */
export const chartColors = {
  primary: '#5e6ad2',
  primaryLight: 'rgba(255, 255, 255, 0.06)',
  ink: '#f4f4f5',
  line: 'rgba(255, 255, 255, 0.1)',
  surface: '#17171a',
  muted: '#71717a',
  mutedInk: '#a1a1aa',
  success: '#27ae60',
  warning: '#f2c94c',
  danger: '#eb5757',
} as const

/**
 * 分类色（多个自习室并排对比时用）。
 * 只取 Linear 品牌紫、提亮紫与四个语义色，保证与全站配色同源且暗底上可辨。
 */
export const categoryColors = [
  '#5e6ad2',
  '#8b5cf6',
  '#27ae60',
  '#f2c94c',
  '#2d9cdb',
  '#eb5757',
] as const

export function seriesColor(index: number): string {
  return categoryColors[index % categoryColors.length] ?? chartColors.primary
}

/** 轴标签统一字号与颜色（12px：低于 12px 在 1440 宽下不可读） */
export const axisLabelStyle = {
  color: chartColors.mutedInk,
  fontSize: 12,
} as const

export const axisLineStyle = {
  lineStyle: {
    color: chartColors.line,
  },
} as const

export const splitLineStyle = {
  lineStyle: {
    color: chartColors.line,
    type: 'dashed' as const,
  },
} as const

/** tooltip 统一底色与描边，避免各图各写一份 */
export const tooltipBase = {
  backgroundColor: chartColors.surface,
  borderColor: chartColors.line,
  borderWidth: 1,
  padding: [8, 10] as [number, number],
  textStyle: {
    color: chartColors.ink,
    fontSize: 12,
  },
} as const

export const legendBase = {
  top: 4,
  itemWidth: 12,
  itemHeight: 8,
  textStyle: {
    color: chartColors.mutedInk,
    fontSize: 12,
  },
} as const

/** 图表统一高度，保持三张图纵向节奏一致 */
export const chartHeight = '300px'

/** 百分比数值统一保留 1 位小数（0.4123 → '41.2%'） */
export function percentText(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`
}

