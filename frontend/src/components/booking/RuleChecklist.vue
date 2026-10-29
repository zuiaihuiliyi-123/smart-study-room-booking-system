<script setup lang="ts">
import { CircleCheckFilled, CircleCloseFilled, QuestionFilled } from '@element-plus/icons-vue'
import type { Component } from 'vue'

import type { JudgementItem, JudgementState } from '@/utils/bookingRules'

defineProps<{ items: JudgementItem[] }>()

const STATE_ICON: Record<JudgementState, Component> = {
  pass: CircleCheckFilled,
  fail: CircleCloseFilled,
  unknown: QuestionFilled,
}

const STATE_TEXT: Record<JudgementState, string> = {
  pass: '通过',
  fail: '未通过',
  unknown: '未判定',
}
</script>

<template>
  <ol class="rule-list">
    <li
      v-for="item in items"
      :key="item.id"
      class="rule-item"
      :class="`rule-item--${item.state}`"
    >
      <div class="rule-item__body">
        <p class="rule-item__head">
          <strong>{{ item.title }}</strong>
          <span class="rule-item__state">
            <el-icon><component :is="STATE_ICON[item.state]" /></el-icon>
            {{ STATE_TEXT[item.state] }}
          </span>
        </p>

        <p class="rule-item__cond">判定条件：{{ item.condition }}</p>

        <p class="rule-item__detail">{{ item.detail }}</p>

        <ul v-if="item.bullets.length" class="rule-item__bullets">
          <li v-for="bullet in item.bullets" :key="bullet">{{ bullet }}</li>
        </ul>
      </div>
    </li>
  </ol>
</template>

<style scoped>
.rule-list {
  padding: 0;
  margin: 0;
  list-style: none;
}

.rule-item {
  display: flex;
  gap: 10px;
  padding: 8px 0;
}

.rule-item + .rule-item {
  border-top: 1px dashed var(--ssr-line);
}

.rule-item__body {
  min-width: 0;
}

.rule-item__head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  margin: 0;
}

.rule-item__head strong {
  font-size: 13.5px;
}

.rule-item__state {
  display: inline-flex;
  gap: 3px;
  align-items: center;
  font-size: 11.5px;
  font-weight: 600;
}

.rule-item--pass .rule-item__state {
  color: var(--ssr-success);
}

.rule-item--fail .rule-item__state {
  color: var(--ssr-danger);
}

.rule-item--unknown .rule-item__state {
  color: var(--ssr-muted-ink);
}

.rule-item__cond,
.rule-item__detail {
  margin: 3px 0 0;
  font-size: var(--ssr-font-note);
}

.rule-item__cond {
  color: var(--ssr-muted-ink);
}

.rule-item__detail {
  color: var(--ssr-ink);
}

.rule-item__bullets {
  padding-left: 16px;
  margin: 4px 0 0;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
  line-height: 1.7;
}
</style>
