<script setup lang="ts">
/**
 * 数据看板（FR-050～FR-053 / NFR-001 / BR-016）。
 *
 * 「10 秒」是**数据读取周期**，与「违约判定扫描周期 ≤1 分钟」不是一回事：
 * 页面因此必须给出「数据截至时间」，避免把 10 秒前读到、1 分钟前算出的数字当成实时值。
 * 刷新机制（防重入 / 可见性暂停 / 失败保留旧数据）全部在 `useDashboard.ts`，本页只负责展示。
 */
import { computed } from 'vue'

import BaseChart from '@/components/BaseChart.vue'
import EmptyState from '@/components/EmptyState.vue'
import FilterBar from '@/components/FilterBar.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import PageHeader from '@/components/PageHeader.vue'
import DashboardStatusBar from '@/components/admin/DashboardStatusBar.vue'
import StatCard from '@/components/StatCard.vue'
import { chartHeight } from '@/utils/chartTheme'
import { formatTimeSecond, isAfterToday } from '@/utils/format'
import { REFRESH_INTERVAL_MS, TOP_N, useDashboard } from '@/utils/useDashboard'
import { useDashboardCharts } from '@/utils/dashboardCharts'

const {
  scopeLabel,
  roomOptions,
  dateRange,
  roomId,
  cardItems,
  seatUsage,
  trend,
  topViolators,
  violationSample,
  violationsTruncated,
  loading,
  inFlight,
  errorMessage,
  lastUpdatedAt,
  staleSince,
  hasData,
  refreshCount,
  countdown,
  paused,
  refreshNow,
  applyFilters,
  resetFilters,
} = useDashboard()

const { seatUsageOption, trendOption, topViolatorsOption } = useDashboardCharts({
  seatUsage,
  trend,
  topViolators,
})

const refreshCycleText = `${REFRESH_INTERVAL_MS / 1000} 秒`

/** 数据截至时间：只看**最后一次成功读取**的时刻（IR-004：失败时保留上一次数据） */
const updatedText = computed(() =>
    lastUpdatedAt.value === null ? '--:--:--' : formatTimeSecond(lastUpdatedAt.value),
)
const staleText = computed(() =>
    staleSince.value === null ? '' : formatTimeSecond(staleSince.value),
)

function disabledDate(value: Date): boolean {
  return isAfterToday(value)
}

const topSourceText = computed(() => {
  if (violationSample.value === 0) return '所选区间内没有违约记录'
  const extra = violationsTruncated.value ? '（超过分页上限，仅统计前 1000 条）' : ''
  return `数据来源：由 /violations 明细聚合（所选区间共 ${violationSample.value} 条，取前 ${TOP_N} 名）${extra}；后端暂无 Top N 接口，且该接口无自习室参数，因此图 3 为全站口径（不受上方「自习室」筛选影响）`
})

/* ---------- 图表的读屏描述（canvas 对读屏不可读，用一句话交代「图在讲什么」） ---------- */
const seatUsageLabel = computed(
  () =>
    `柱状图：各自习室各时段座位占用率，统计周期 ${dateRange.value[0]} 至 ${dateRange.value[1]}，数据截至 ${updatedText.value}。具体数值见页面下方口径说明与提示框。`,
)
const trendLabel = computed(
  () =>
    `双折线图：近 ${trend.value.length} 个自然日的每日有效预约数与每日违约数趋势，数据截至 ${updatedText.value}。`,
)
const topViolatorsLabel = computed(
  () =>
    `横向条形图：用户违约次数前 ${TOP_N} 名（${violationSample.value} 条违约记录聚合），数据截至 ${updatedText.value}。`,
)
</script>

<template>
  <div class="page">
    <PageHeader
      title="数据看板"
      subtitle="统计口径 · 数据读取周期 10 秒（不是违约判定周期，后者由后端扫描，≤1 分钟）"
    />

    <!-- 顶部状态条：数据截至时间 / 自动刷新次数 / 下次刷新倒计时 / 手动刷新 -->
    <DashboardStatusBar
      :updated-text="updatedText"
      :refresh-count="refreshCount"
      :countdown="countdown"
      :cycle-text="refreshCycleText"
      :in-flight="inFlight"
      :paused="paused"
      @refresh="refreshNow"
    />

    <!-- 失败但仍有旧数据：保留图表，只提示数据时刻（IR-004：不得以 0 值代替故障） -->
    <el-alert
      v-if="staleSince"
      class="dash-alert"
      type="warning"
      :closable="false"
      show-icon
      :title="`更新失败，显示 ${staleText} 的数据`"
      :description="`最近一次读取失败，页面保留 ${staleText} 读取到的数据，不会清空图表；系统会在 ${refreshCycleText}后重试。`"
    />

    <FilterBar :loading="inFlight" @search="applyFilters" @reset="resetFilters">
      <label class="filter-field">
        <span class="filter-field__label">统计周期</span>
        <el-date-picker
          v-model="dateRange"
          class="w-260"
          type="daterange"
          value-format="YYYY-MM-DD"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          :disabled-date="disabledDate"
        />
      </label>
      <label class="filter-field">
        <span class="filter-field__label">自习室</span>
        <el-select v-model="roomId" class="w-170">
          <el-option label="全部自习室" value="all" />
          <el-option v-for="room in roomOptions" :key="room.id" :label="room.name" :value="room.id" />
        </el-select>
      </label>
      <template #actions>
        <span class="ssr-text-muted dash-scope">操作范围：{{ scopeLabel }}</span>
      </template>
    </FilterBar>

    <!-- 首次加载 -->
    <LoadingBlock v-if="loading && !hasData" :rows="6" min-height="320px" text="正在读取看板数据" />

    <!-- 首次加载即失败：给重试入口，同时说明自动重试 -->
    <el-alert
      v-else-if="!hasData"
      class="dash-alert"
      type="error"
      :closable="false"
      show-icon
      title="看板数据读取失败"
      :description="`${errorMessage}（每 ${refreshCycleText}自动重试一次，也可点上方「立即刷新」）`"
    />

    <template v-else>
      <!-- 5 项概览（FR-052） -->
      <div class="dash-cards">
        <StatCard
          v-for="card in cardItems"
          :key="card.key"
          :label="card.label"
          :value="card.count"
          :unit="card.unit"
          :hint="card.hint"
          :tone="card.tone"
          :footnote="`截至 ${updatedText}`"
        />
      </div>

      <!-- 图 1 -->
      <section class="ssr-card dash-chart">
        <div class="ssr-card__head">
          <h3>图 1　各自习室各时段座位占用率</h3>
          <span class="ssr-text-muted">统计周期 {{ dateRange[0] }} 至 {{ dateRange[1] }}</span>
        </div>
        <EmptyState
          v-if="seatUsage.length === 0"
          description="所选周期与自习室内没有可统计的座位数据"
        />
        <BaseChart
          v-else
          :option="seatUsageOption"
          :height="chartHeight"
          :label="seatUsageLabel"
        />
        <p class="dash-caption">
          口径：占用率 = 被「待使用 / 使用中 / 已完成」预约覆盖的 30 分钟座位块数 ÷
          （座位数 × 时段块数 × 统计天数）；已取消与已违约的预约不占用时段。
          纵轴按所选范围的实际最大值自适应（不锁 100%），绝对值见 tooltip。
        </p>
      </section>

      <!-- 图 2 -->
      <section class="ssr-card dash-chart">
        <div class="ssr-card__head">
          <h3>图 2　近 7 天预约量与违约量趋势</h3>
          <span class="ssr-text-muted">按自然日</span>
        </div>
        <EmptyState v-if="trend.length === 0" description="所选周期内没有预约与违约记录" />
        <BaseChart
          v-else
          :option="trendOption"
          :height="chartHeight"
          :label="trendLabel"
        />
        <p class="dash-caption">
          口径：每日有效预约数 = 当日创建且未被取消的预约单；每日违约数 = 当日产生的违约记录（自动 + 手动）。
          无记录的日期取 0 而非断点。
        </p>
      </section>

      <!-- 图 3 -->
      <section class="ssr-card dash-chart">
        <div class="ssr-card__head">
          <h3>图 3　用户违约次数 Top {{ TOP_N }}</h3>
          <span class="ssr-text-muted">横向条形 · 次数越多越靠上</span>
        </div>
        <EmptyState v-if="topViolators.length === 0" description="所选区间内没有违约记录" />
        <BaseChart
          v-else
          :option="topViolatorsOption"
          :height="chartHeight"
          :label="topViolatorsLabel"
        />
        <p class="dash-caption">{{ topSourceText }}</p>
      </section>

      <el-alert class="dash-alert" type="info" :closable="false" show-icon title="关于「10 秒」的口径">
        <p>
          <strong>{{ refreshCycleText }}</strong> 是<strong>数据读取周期</strong>
          （唯一有原文来源的量化指标），只决定本页多久重新拉一次聚合值；
          违约判定由后端扫描任务负责，周期 ≤1 分钟，与本页刷新无关。
        </p>
        <p>
          因此任何数字都以「数据截至时间」为准：失败时保留上一次成功读取的数据并提示该时刻，<strong>不会用 0 值冒充故障</strong>。
          页面切到后台会暂停倒计时，切回时立即读取一次并恢复 {{ refreshCycleText }}周期。
        </p>
      </el-alert>
    </template>
  </div>
</template>

<style scoped>

.dash-alert {
  margin-bottom: 12px;
}

.dash-scope {
  font-size: var(--ssr-font-note);
}

.dash-cards {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.dash-chart {
  margin-bottom: 12px;
}

.dash-caption {
  margin: 4px 0 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  line-height: 1.7;
}

@media (max-width: 1200px) {
  .dash-cards {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}
</style>








