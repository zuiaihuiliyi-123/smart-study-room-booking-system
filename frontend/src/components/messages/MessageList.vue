<script setup lang="ts">
import EmptyState from '@/components/EmptyState.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import type { StationMessage } from '@/types'
import { formatDateTime } from '@/utils/format'
import { relatedLabel, relatedObjectText } from '@/utils/messageLinks'

const props = defineProps<{
  items: StationMessage[]
  loading: boolean
  errorMessage: string
  /** 当前筛选条件下的空态文案 */
  emptyText: string
}>()

const emit = defineEmits<{
  (e: 'open', message: StationMessage): void
  (e: 'retry'): void
}>()
</script>

<template>
  <LoadingBlock v-if="props.loading" :rows="5" text="正在读取站内消息…" />

  <div v-else-if="props.errorMessage" class="panel">
    <el-alert type="error" :closable="false" show-icon title="站内消息读取失败">
      <p>{{ props.errorMessage }}</p>
    </el-alert>
    <el-button type="primary" plain @click="emit('retry')">重试</el-button>
  </div>

  <EmptyState v-else-if="props.items.length === 0" :description="props.emptyText" />

  <ul v-else class="list">
    <li
      v-for="item in props.items"
      :key="item.id"
      class="msg"
      :class="{ 'msg--unread': !item.is_read }"
    >
      <button class="msg__btn" type="button" @click="emit('open', item)">
        <span class="msg__side">
          <span v-if="!item.is_read" class="ssr-unread-dot" aria-hidden="true" />
        </span>

        <span class="msg__main">
          <span class="msg__head">
            <strong class="msg__title">{{ item.title }}</strong>
            <el-tag v-if="!item.is_read" size="small" effect="plain">未读</el-tag>
            <el-tag size="small" type="info" effect="plain">{{ item.type }}</el-tag>
            <span class="ssr-text-muted">{{ formatDateTime(item.created_at) }}</span>
          </span>

          <span class="msg__body">{{ item.content }}</span>

          <span class="msg__foot">
            <span class="ssr-text-muted">{{ relatedObjectText(item) || '无关联对象' }}</span>
            <span class="msg__link">{{ relatedLabel(item.related_type) }} →</span>
          </span>
        </span>
      </button>
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
  padding: 0;
  margin: 0;
  overflow: hidden;
  list-style: none;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.list li + li {
  border-top: 1px solid var(--ssr-line);
}

.msg__btn {
  display: flex;
  gap: 10px;
  width: 100%;
  padding: 12px 14px;
  font-family: inherit;
  text-align: left;
  background: transparent;
  border: 0;
  cursor: pointer;
}

.msg--unread {
  background: var(--ssr-primary-light);
}

.msg__btn:hover {
  background: var(--ssr-primary-light);
}

.msg__side {
  display: flex;
  flex: 0 0 10px;
  align-items: center;
  padding-top: 6px;
}

.msg__main {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.msg__head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.msg__title {
  font-size: 13.5px;
  font-weight: 500;
}

.msg--unread .msg__title {
  font-weight: 700;
}

.msg__body {
  color: var(--ssr-ink);
  font-size: var(--ssr-font-note);
  line-height: 1.65;
}

.msg__foot {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  justify-content: space-between;
  font-size: var(--ssr-font-note);
}

.msg__link {
  color: var(--ssr-primary);
  font-weight: 600;
}
</style>
