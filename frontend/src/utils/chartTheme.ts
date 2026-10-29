/**
 * 图表主题（AGENTS.md §3.8：图表色值集中在 `src/utils/chartTheme.ts`，视图里禁止散落十六进制）。
 *
 * 色值真值源是 `src/assets/styles/index.scss` 第 1 节的 SCSS 变量，本文件是它在 ECharts 侧的
 * 唯一投影。ECharts 的 option 只能吃具体色值字符串，无法直接写 `var(--ssr-primary)`，
 * 因此改色时**两处必须同步**（这条约定写在 index.scss 文件头）。
 */

/** 与 index.scss 第 1 节一一对应 */
export const chartColors = {
  primary: '#2b5f9e',
  primaryLight: '#eaf2fb',
  ink: '#12304f',
  line: '#d6e2f0',
  surface: '#ffffff',
  muted: '#6b7a8d',
  mutedInk: '#5a6879',
  success: '#1b7a45',
  warning: '#a9720b',
  danger: '#b3261e',
} as const

/**
 * 分类色（多个自习室并排对比时用）。
 * 刻意避开状态色语义，只取主色深浅与低饱和辅助色，保证与全站配色同源。
 */
export const categoryColors = [
  '#2b5f9e',
  '#1b7a45',
  '#a9720b',
  '#6b3fa0',
  '#0f7a83',
  '#96500a',
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

