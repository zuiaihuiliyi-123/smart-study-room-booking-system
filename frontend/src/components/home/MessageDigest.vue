<script setup lang="ts">
import EmptyState from '@/components/EmptyState.vue'
import LoadingBlock from '@/components/LoadingBlock.vue'
import type { StationMessage } from '@/types'
import { formatDateTime } from '@/utils/format'
import { relatedLabel } from '@/utils/messageLinks'

const props = defineProps<{
  /** 未读消息（最多 3 条） */
  messages: StationMessage[]
  unreadTotal: number
  loading: boolean
  errorMessage: string
}>()

const emit = defineEmits<{
  (e: 'open', message: StationMessage): void
  (e: 'retry'): void
}>()
</script>

<template>
  <section class="digest">
    <header class="digest__head">
      <h3>未读消息</h3>
      <span v-if="props.unreadTotal > 0" class="digest__badge">{{ props.unreadTotal }} 条未读</span>
      <span v-else class="ssr-text-muted">全部已读</span>
    </header>

    <LoadingBlock v-if="props.loading" :rows="3" text="正在读取站内消息…" />

    <div v-else-if="props.errorMessage" class="digest__panel">
      <el-alert type="error" :closable="false" show-icon title="站内消息读取失败">
        <p>{{ props.errorMessage }}</p>
      </el-alert>
      <el-button type="primary" plain @click="emit('retry')">重试</el-button>
    </div>

    <EmptyState
      v-else-if="props.messages.length === 0"
      description="没有未读消息"
      :image-size="60"
    />

    <template v-else>
      <ul class="digest__list">
        <li v-for="message in props.messages" :key="message.id">
          <button class="digest__item" type="button" @click="emit('open', message)">
            <span class="digest__item-head">
              <strong>{{ message.title }}</strong>
              <em>{{ message.type }}</em>
            </span>
            <span class="digest__item-body">{{ message.content }}</span>
            <span class="digest__item-foot">
              <span class="ssr-text-muted">{{ formatDateTime(message.created_at) }}</span>
              <span class="digest__item-link">{{ relatedLabel(message.related_type) }} →</span>
            </span>
          </button>
        </li>
      </ul>

      <p class="ssr-text-muted digest__note">
        点击消息会标记为已读，并按关联对象跳转到对应列表页（列表内高亮该条记录）；全部消息可在侧栏
        「我的记录 → 站内消息」查看。未读数与顶栏铃铛角标共用同一份数据。
      </p>
    </template>
  </section>
</template>

<style scoped>
.digest {
  padding: 14px 16px;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
}

.digest__head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 8px;
  margin-bottom: 10px;
  border-bottom: 1px solid var(--ssr-line);
}

.digest__head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.digest__badge {
  padding: 1px 8px;
  color: var(--ssr-danger);
  font-size: var(--ssr-font-note);
  font-weight: 600;
  background: var(--ssr-danger-bg);
  border-radius: 10px;
}

.digest__panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  align-items: flex-start;
}

.digest__list {
  padding: 0;
  margin: 0;
  list-style: none;
}

.digest__list li + li {
  border-top: 1px dashed var(--ssr-line);
}

.digest__item {
  display: block;
  width: 100%;
  padding: 9px 6px;
  font-family: inherit;
  text-align: left;
  background: transparent;
  border: 0;
  border-radius: var(--ssr-radius-sm);
  cursor: pointer;
}

.digest__item:hover {
  background: var(--ssr-primary-light);
}

.digest__item-head {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  justify-content: space-between;
}

.digest__item-head strong {
  font-size: 13.5px;
}

.digest__item-head em {
  color: var(--ssr-muted-ink);
  font-size: 11.5px;
  font-style: normal;
}

.digest__item-body {
  display: -webkit-box;
  margin-top: 3px;
  overflow: hidden;
  color: var(--ssr-ink);
  font-size: var(--ssr-font-note);
  line-height: 1.6;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.digest__item-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  justify-content: space-between;
  margin-top: 4px;
}

.digest__item-link {
  color: var(--ssr-primary);
  font-size: var(--ssr-font-note);
  font-weight: 600;
}

.digest__note {
  padding-top: 8px;
  margin: 8px 0 0;
  border-top: 1px dashed var(--ssr-line);
}
</style>
