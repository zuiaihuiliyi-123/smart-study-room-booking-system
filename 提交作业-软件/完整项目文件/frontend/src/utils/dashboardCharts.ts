/**
 * 看板三张图的 ECharts option（FR-050 / FR-051 / 图 3）。
 *
 * 约束（AGENTS.md §3.8 + 本轮任务）：
 * - 视图里不出现十六进制色值，颜色一律来自 `chartTheme.ts`，并按当前主题取色；
 * - option 用 `computed` 生成并标注 `EChartsOption`，数据或主题变化只换 option、不重建图表实例。
 */
import { computed, type Ref } from 'vue'
import type { EChartsOption } from 'echarts'

import type { SeatUsageSlotRow, TrendPoint, ViolationTopEntry } from '@/types'
import {
  chartPaletteOf,
  chartStylesOf,
  seriesColor,
  type ChartPalette,
  type ChartStyles,
} from '@/utils/chartTheme'
import { useTheme, type ThemeMode } from '@/utils/useTheme'

/** 图 1 单根柱子的数据项：除百分比外还带占用/容量，供 tooltip 解释口径 */
interface UsageBarDatum {
  value: number
  occupied: number
  capacity: number
}

/** 图 1：各自习室 × 各时段座位占用率（分组柱状） */
export function seatUsageOptionOf(rows: SeatUsageSlotRow[], mode: ThemeMode): EChartsOption {
  const palette: ChartPalette = chartPaletteOf(mode)
  const styles: ChartStyles = chartStylesOf(mode)

  const slots: string[] = []
  for (const row of rows) {
    if (!slots.includes(row.slot)) slots.push(row.slot)
  }

  const rooms: number[] = []
  for (const row of rows) {
    if (!rooms.includes(row.room_id)) rooms.push(row.room_id)
  }

  const series = rooms.map((id, index) => {
    const roomName = rows.find((row) => row.room_id === id)?.room_name ?? `自习室 #${id}`
    return {
      name: roomName,
      type: 'bar' as const,
      barMaxWidth: 26,
      itemStyle: { color: seriesColor(mode, index), borderRadius: [2, 2, 0, 0] as [number, number, number, number] },
      data: slots.map((slot) => {
        const row = rows.find((item) => item.room_id === id && item.slot === slot)
        const datum: UsageBarDatum = {
          value: Number(((row?.rate ?? 0) * 100).toFixed(1)),
          occupied: row?.occupied ?? 0,
          capacity: row?.capacity ?? 0,
        }
        return datum
      }),
    }
  })

  return {
    tooltip: {
      ...styles.tooltipBase,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const list = (Array.isArray(params) ? params : [params]) as {
          axisValueLabel?: string
          seriesName?: string
          data?: unknown
        }[]
        const title = list[0]?.axisValueLabel ?? ''
        const lines = list.map((item) => {
          const datum = item.data as UsageBarDatum | undefined
          const capacity = datum?.capacity ?? 0
          const detail =
            capacity > 0
              ? `${datum?.occupied ?? 0} / ${capacity} 个 30 分钟座位块`
              : '该自习室暂无座位'
          return `${item.seriesName ?? ''}：${(datum?.value ?? 0).toFixed(1)}%（${detail}）`
        })
        return [title, ...lines].join('<br/>')
      },
    },
    legend: { ...styles.legendBase },
    grid: { left: 8, right: 16, top: 40, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category',
      data: slots,
      axisLabel: { ...styles.axisLabelStyle, interval: 0 },
      axisLine: styles.axisLineStyle,
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      name: '占用率',
      nameTextStyle: { ...styles.axisLabelStyle },
      min: 0,
      // 不锁死 100%：示范数据下占用率往往是个位数百分比，锁 100% 会让柱子矮到看不见。
      // 纵轴按实际最大值自适应，tooltip 里给出「占用块数 / 容量」绝对值，避免误读。
      axisLabel: { ...styles.axisLabelStyle, formatter: '{value}%' },
      axisLine: { show: false },
      splitLine: styles.splitLineStyle,
    },
    series,
    // 浅色主题在图例/坐标轴上用深一点的文字色，避免白底上发灰
    textStyle: { color: palette.ink },
  }
}

/** 图 2：近 7 天预约量与违约量趋势（双折线） */
export function trendOptionOf(points: TrendPoint[], mode: ThemeMode): EChartsOption {
  const palette = chartPaletteOf(mode)
  const styles = chartStylesOf(mode)
  const dates = points.map((point) => point.date.slice(5))
  return {
    tooltip: { ...styles.tooltipBase, trigger: 'axis' },
    legend: { ...styles.legendBase, data: ['每日预约数', '每日违约数'] },
    grid: { left: 8, right: 16, top: 40, bottom: 8, containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLabel: styles.axisLabelStyle,
      axisLine: styles.axisLineStyle,
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      name: '笔',
      nameTextStyle: styles.axisLabelStyle,
      minInterval: 1,
      axisLabel: styles.axisLabelStyle,
      axisLine: { show: false },
      splitLine: styles.splitLineStyle,
    },
    series: [
      {
        name: '每日预约数',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        itemStyle: { color: palette.primary },
        lineStyle: { width: 2 },
        areaStyle: { color: palette.primary, opacity: 0.08 },
        data: points.map((point) => point.reservations),
      },
      {
        name: '每日违约数',
        type: 'line',
        smooth: true,
        symbolSize: 6,
        itemStyle: { color: palette.danger },
        lineStyle: { width: 2 },
        areaStyle: { color: palette.danger, opacity: 0.08 },
        data: points.map((point) => point.violations),
      },
    ],
  }
}

/** 图 3：用户违约次数 Top N（横向条形，按次数升序排列以便最大值在上方） */
export function topViolatorsOptionOf(
  entries: ViolationTopEntry[],
  mode: ThemeMode,
): EChartsOption {
  const palette = chartPaletteOf(mode)
  const styles = chartStylesOf(mode)
  // yAxis 从下往上绘制，倒序后次数最多的排在最上方
  const ordered = [...entries].reverse()
  return {
    tooltip: {
      ...styles.tooltipBase,
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const list = (Array.isArray(params) ? params : [params]) as {
          dataIndex?: number
          value?: unknown
        }[]
        const index = list[0]?.dataIndex ?? 0
        const entry = ordered[index]
        if (!entry) return ''
        return `${entry.name}（${entry.student_no}）<br/>累计违约 ${entry.count} 次`
      },
    },
    grid: { left: 8, right: 40, top: 16, bottom: 8, containLabel: true },
    xAxis: {
      type: 'value',
      minInterval: 1,
      axisLabel: styles.axisLabelStyle,
      axisLine: { show: false },
      splitLine: styles.splitLineStyle,
    },
    yAxis: {
      type: 'category',
      data: ordered.map((entry) => entry.name),
      axisLabel: styles.axisLabelStyle,
      axisLine: styles.axisLineStyle,
      axisTick: { show: false },
    },
    series: [
      {
        name: '违约次数',
        type: 'bar',
        barMaxWidth: 16,
        itemStyle: {
          color: palette.danger,
          borderRadius: [0, 2, 2, 0] as [number, number, number, number],
        },
        label: { show: true, position: 'right', color: palette.mutedInk, fontSize: 12 },
        data: ordered.map((entry) => entry.count),
      },
    ],
  }
}

/** 三张图统一出口：视图只绑定这几个 computed，主题切换会自动重算 option */
export function useDashboardCharts(source: {
  seatUsage: Ref<SeatUsageSlotRow[]>
  trend: Ref<TrendPoint[]>
  topViolators: Ref<ViolationTopEntry[]>
}) {
  const { mode } = useTheme()
  const seatUsageOption = computed<EChartsOption>(() =>
    seatUsageOptionOf(source.seatUsage.value, mode.value),
  )
  const trendOption = computed<EChartsOption>(() => trendOptionOf(source.trend.value, mode.value))
  const topViolatorsOption = computed<EChartsOption>(() =>
    topViolatorsOptionOf(source.topViolators.value, mode.value),
  )
  return { seatUsageOption, trendOption, topViolatorsOption }
}
