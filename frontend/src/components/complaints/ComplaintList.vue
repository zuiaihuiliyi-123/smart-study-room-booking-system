<script setup lang="ts">

import EmptyState from '@/components/EmptyState.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import StatusTag from '@/components/StatusTag.vue'
import { complaintTimeline } from '@/components/complaints/complaintMeta'
import { formatDateTime } from '@/utils/format'
import type { Complaint } from '@/types'

const props = defineProps<{
  items: Complaint[]
  loading: boolean
  errorMessage: string
  /** 刚提交成功的投诉编号：高亮该条 */
  newId: number | null
  /** 从站内消息跳转过来时高亮的投诉编号 */
  focusId: number | null
}>()

const emit = defineEmits<{ (e: 'retry'): void }>()

function isHighlighted(item: Complaint): boolean {
  return item.id === props.newId || item.id === props.focusId
}
</script>

<template>
  <LoadingBlock v-if="props.loading" :rows="5" text="正在读取投诉记录…" />

  <div v-else-if="props.errorMessage" class="panel">
    <el-alert type="error" :closable="false" show-icon title="投诉记录读取失败">
      <p>{{ props.errorMessage }}</p>
    </el-alert>
    <el-button type="primary" plain @click="emit('retry')">重试</el-button>
  </div>

  <EmptyState
    v-else-if="props.items.length === 0"
    description="还没有提交过投诉；在上方表单填写对象与内容即可提交"
  />

  <ul v-else class="list">
    <li
      v-for="item in props.items"
      :key="item.id"
      class="complaint"
      :class="{ 'complaint--new': isHighlighted(item) }"
    >
      <header class="complaint__head">
        <span class="complaint__title">投诉 #{{ item.id }}</span>
        <StatusTag kind="complaint" :value="item.status" />
        <span class="ssr-text-muted">
          {{ item.target_type }} #{{ item.target_id }} · 提交于
          {{ formatDateTime(item.created_at) }}
        </span>
      </header>

      <p class="complaint__content">{{ item.content }}</p>

      <dl class="complaint__handling">
        <div>
          <dt>处理说明</dt>
          <dd>{{ item.handle_note ?? '暂无（尚未受理）' }}</dd>
        </div>
        <div>
          <dt>处理时间</dt>
          <dd>
            {{ item.handled_at ? formatDateTime(item.handled_at) : '—' }}
          </dd>
        </div>
      </dl>

      <el-timeline class="complaint__timeline">
        <el-timeline-item
          v-for="(step, index) in complaintTimeline(item)"
          :key="`${item.id}-${index}`"
          :type="step.type"
          :timestamp="step.time ? formatDateTime(step.time) : '时刻未记录'"
          :hollow="step.time === ''"
          placement="top"
        >
          <span class="complaint__step">{{ step.title }}</span>
          <span class="ssr-text-muted">{{ step.note }}</span>
        </el-timeline-item>
      </el-timeline>
    </li>
  </ul>
</template>

<style scoped>
.panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
  padding: 14px 16px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.panel p {
  margin: 0;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0;
  margin: 0;
  list-style: none;
}

.complaint {
  padding: 12px 14px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.complaint--new {
  border-color: var(--ssr-warning);
  box-shadow: 0 0 0 2px var(--ssr-warning-bg);
  animation: ssr-row-flash 2.4s ease-out 1;
}

.complaint__head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.complaint__title {
  font-size: 14px;
  font-weight: 600;
}

.complaint__content {
  margin: 8px 0;
  font-size: var(--ssr-font-note);
  line-height: 1.7;
}

.complaint__handling {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 180px);
  gap: 6px 14px;
  padding: 8px 10px;
  margin: 0 0 10px;
  background: var(--ssr-bg);
  border-radius: var(--ssr-radius-sm);
}

.complaint__handling div {
  display: flex;
  gap: 6px;
  min-width: 0;
}

.complaint__handling dt {
  flex: 0 0 auto;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

.complaint__handling dd {
  margin: 0;
  font-size: var(--ssr-font-note);
}

.complaint__timeline {
  padding-left: 2px;
  margin-bottom: -18px;
}

.complaint__step {
  margin-right: 8px;
  font-size: var(--ssr-font-note);
  font-weight: 600;
}

@media (max-width: 768px) {
  .complaint__handling {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>


