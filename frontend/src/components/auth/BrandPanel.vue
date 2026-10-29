<script setup lang="ts">
/**
 * 登录页左侧品牌区（从 LoginView 抽出，LoginView 因此回到 300 行以内）。
 *
 * 注意：不得使用浙江大学校徽 / 校名标准化字体等受保护素材（AGENTS.md §3.9），
 * 标记为自绘 SVG 占位图形。
 */
const capabilities = [
  { id: '01', text: '30 分钟粒度选座，提前 7 天可预约，单次最长 4 小时' },
  { id: '02', text: '开始前后 15 分钟窗口内签到，累计 3 次违约自动限制 7 天' },
  { id: '03', text: '站内消息提醒、投诉处理，管理端数据看板每 10 秒刷新' },
]
</script>

<template>
  <section class="brand">
    <div class="brand__inner">
      <svg class="brand__mark" viewBox="0 0 48 48" aria-hidden="true" focusable="false">
        <rect x="1.5" y="1.5" width="45" height="45" rx="12" fill="none" stroke="currentColor" stroke-width="2.5" />
        <rect x="10" y="13" width="28" height="4" rx="2" fill="currentColor" />
        <rect x="12" y="22" width="8" height="13" rx="2" fill="currentColor" />
        <rect x="28" y="22" width="8" height="13" rx="2" fill="currentColor" />
      </svg>

      <h1>智慧自习室预约与管理系统</h1>
      <p class="brand__sub">Smart Study Room Booking &amp; Management System</p>

      <ul class="brand__caps">
        <li v-for="item in capabilities" :key="item.id">
          <span class="brand__cap-id" aria-hidden="true">{{ item.id }}</span>
          <span>{{ item.text }}</span>
        </li>
      </ul>

      <p class="brand__foot">课程项目 · 惊蛰破阵曲 · 界面演示版</p>
    </div>
  </section>
</template>

<style scoped>
.brand {
  display: flex;
  flex: 0 0 60%;
  align-items: center;
  min-width: 0;
  padding: 48px 56px;
  color: var(--ssr-on-primary);
  background: linear-gradient(
  155deg,
  var(--ssr-primary) 0%,
  var(--ssr-primary-deep) 62%,
  var(--ssr-ink) 100%
  );
}

.brand__inner {
  max-width: 520px;
}

.brand__mark {
  width: 56px;
  height: 56px;
}

h1 {
  margin: 20px 0 0;
  font-size: 26px;
  font-weight: 600;
  line-height: 1.35;
}

.brand__sub {
  margin: 8px 0 0;
  font-size: var(--ssr-font-note);
  opacity: 0.85;
}

.brand__caps {
  padding: 0;
  margin: 28px 0 0;
  list-style: none;
}

.brand__caps li {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
  font-size: var(--ssr-font-body);
  line-height: 1.6;
}

.brand__cap-id {
  flex: 0 0 auto;
  padding: 1px 7px;
  color: var(--ssr-primary-deep);
  font-size: var(--ssr-font-note);
  /* 白底深蓝字（8.74:1）；18% 白底 + 白字只有 4.32:1，不达 AA */
  background: var(--ssr-on-primary);
  border-radius: 10px;
}

.brand__foot {
  margin: 32px 0 0;
  font-size: var(--ssr-font-note);
  opacity: 0.75;
}
</style>
