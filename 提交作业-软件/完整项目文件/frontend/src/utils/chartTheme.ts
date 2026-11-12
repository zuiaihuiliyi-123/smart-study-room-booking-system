/**
 * 图表主题（AGENTS.md §3.8：图表色值集中在 `src/utils/chartTheme.ts`，视图里禁止散落十六进制）。
 *
 * 色值真值源是 `src/assets/styles/index.scss` 第 1 节的令牌表（$tokens-light / $tokens-dark），
 * 本文件是它在 ECharts 侧的唯一投影。ECharts 只能吃具体色值字符串、写不了 `var(--ssr-*)`，
 * 所以这里按主题各存一份调色板；option 由 `dashboardCharts.ts` 按当前主题生成。
 */
import type { ThemeMode } from '@/utils/useTheme'

export interface ChartPalette {
  primary: string
  primaryLight: string
  ink: string
  line: string
  surface: string
  muted: string
  mutedInk: string
  success: string
  warning: string
  danger: string
}

/** 浅色：与 notion-style 的令牌一一对应（米色底 + 暖黑文字 + 靛紫主色） */
const lightPalette: ChartPalette = {
  primary: '#4c56c4',
  primaryLight: '#eeeffb',
  ink: '#37352f',
  line: 'rgba(55, 53, 47, 0.1)',
  surface: '#ffffff',
  muted: '#9b9a97',
  mutedInk: '#6b6a66',
  success: '#0f7b6c',
  warning: '#8f6a02',
  danger: '#c0392b',
}

/** 暗色：与 linear-style 的令牌一一对应（近黑底 + zinc 文字 + 靛紫主色） */
const darkPalette: ChartPalette = {
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
}

export const chartPalettes: Record<ThemeMode, ChartPalette> = {
  light: lightPalette,
  dark: darkPalette,
}

export function chartPaletteOf(mode: ThemeMode): ChartPalette {
  return mode === 'dark' ? darkPalette : lightPalette
}

/**
 * 分类色（多个自习室并排对比时用）。
 * 只取品牌靛紫、提亮紫与四个语义色，保证与全站配色同源、且在各主题底色上可辨。
 */
const lightCategoryColors = ['#4c56c4', '#5e6ad2', '#0f7b6c', '#8f6a02', '#2d7dd2', '#c0392b']
const darkCategoryColors = ['#5e6ad2', '#8b5cf6', '#27ae60', '#f2c94c', '#2d9cdb', '#eb5757']

export function categoryColorsOf(mode: ThemeMode): readonly string[] {
  return mode === 'dark' ? darkCategoryColors : lightCategoryColors
}

export function seriesColor(mode: ThemeMode, index: number): string {
  const colors = categoryColorsOf(mode)
  return colors[index % colors.length] ?? chartPaletteOf(mode).primary
}

export interface ChartStyles {
  /** 轴标签统一字号与颜色（12px：再小在 1440 宽下不可读） */
  axisLabelStyle: { color: string; fontSize: number }
  axisLineStyle: { lineStyle: { color: string } }
  splitLineStyle: { lineStyle: { color: string; type: 'dashed' } }
  /** tooltip 统一底色与描边，避免各图各写一份 */
  tooltipBase: {
    backgroundColor: string
    borderColor: string
    borderWidth: number
    padding: [number, number]
    textStyle: { color: string; fontSize: number }
  }
  legendBase: {
    top: number
    itemWidth: number
    itemHeight: number
    textStyle: { color: string; fontSize: number }
  }
}

export function chartStylesOf(mode: ThemeMode): ChartStyles {
  const palette = chartPaletteOf(mode)
  return {
    axisLabelStyle: { color: palette.mutedInk, fontSize: 12 },
    axisLineStyle: { lineStyle: { color: palette.line } },
    splitLineStyle: { lineStyle: { color: palette.line, type: 'dashed' } },
    tooltipBase: {
      backgroundColor: palette.surface,
      borderColor: palette.line,
      borderWidth: 1,
      padding: [8, 10],
      textStyle: { color: palette.ink, fontSize: 12 },
    },
    legendBase: {
      top: 4,
      itemWidth: 12,
      itemHeight: 8,
      textStyle: { color: palette.mutedInk, fontSize: 12 },
    },
  }
}

/** 图表统一高度，保持三张图纵向节奏一致 */
export const chartHeight = '300px'

/** 百分比数值统一保留 1 位小数（0.4123 → '41.2%'） */
export function percentText(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`
}
