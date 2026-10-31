<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

import MessageList from '@/components/messages/MessageList.vue'
import PageHeader from '@/components/PageHeader.vue'
import { useMessageStore } from '@/stores/message'
import type { StationMessage } from '@/types'
import { relatedRoute } from '@/utils/messageLinks'

const router = useRouter()
const store = useMessageStore()

const typeFilter = ref('all')
const page = ref(1)
const pageSize = ref(10)

const filtered = computed(() =>
    typeFilter.value === 'all'
    ? store.items
    : store.items.filter((item) => item.type === typeFilter.value),
)
const total = computed(() => filtered.value.length)
const pageItems = computed(() =>
    filtered.value.slice((page.value - 1) * pageSize.value, page.value * pageSize.value),
)
const emptyText = computed(() =>
    typeFilter.value === 'all'
    ? '还没有收到站内消息；预约成功、违约登记、投诉反馈都会在这里提示'
    : `没有「${typeFilter.value}」类型的消息`,
)

function countOf(type: string): number {
  return store.items.filter((item) => item.type === type).length
}

watch(typeFilter, () => {
  page.value = 1
})

// 标记已读会让未读数变化，页码可能越界（例如最后一条被读走后总数不变但筛选结果变了）
watch(total, () => {
  const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value))
  if (page.value > maxPage) page.value = maxPage
})

async function onOpen(message: StationMessage): Promise<void> {
  const target = relatedRoute(message)
  if (!message.is_read) {
    try {
      await store.markRead(message.id)
    } catch {
      // 已读标记失败：拦截器已提示，但仍允许跳转，避免把用户困在列表页
    }
  }
  if (target) {
    void router.push(target)
    return
  }
  ElMessage.info('该消息没有关联对象，已标记为已读')
}

onMounted(() => {
  // 顶栏铃铛已经触发过加载时不会重复请求（store 内部去重）
  void store.load()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="站内消息"
      subtitle="仅站内提示，不接短信 / 邮件 / 微信；用户仅可查看本人的消息"
    >
      <template #actions>
        <span class="ssr-text-muted">
          {{ store.unreadCount }} 条未读 / 共 {{ store.items.length }} 条
        </span>
        <el-button :loading="store.loading" @click="store.load(true)">刷新</el-button>
      </template>
    </PageHeader>

    <el-radio-group v-model="typeFilter" class="types">
      <el-radio-button value="all">全部（{{ store.items.length }}）</el-radio-button>
      <el-radio-button v-for="type in store.types" :key="type" :value="type">
        {{ type }}（{{ countOf(type) }}）
      </el-radio-button>
    </el-radio-group>

    <MessageList
      :items="pageItems"
      :loading="store.loading"
      :error-message="store.errorMessage"
      :empty-text="emptyText"
      @open="onOpen"
      @retry="store.load(true)"
    />

    <div v-if="!store.loading && !store.errorMessage && total > pageSize" class="pager">
      <el-pagination
        background
        layout="total, prev, pager, next"
        :total="total"
        :current-page="page"
        :page-size="pageSize"
        @current-change="(next: number) => (page = next)"
      />
    </div>

    <p class="ssr-text-muted note">
      点击消息会标记为已读，并按关联对象跳转到对应列表页（列表内高亮该条记录）。
      未读数与列表使用同一份数据统计，避免角标与列表不一致；标记已读目前只有逐条接口
      <code>POST /messages/{id}/read</code>，没有「全部标为已读」。
    </p>
  </div>
</template>

<style scoped>
.types {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  padding-top: 12px;
}

.note {
  padding: 10px 12px;
  margin: 14px 0 0;
  line-height: 1.7;
  background: var(--ssr-bg);
  border-radius: var(--ssr-radius-sm);
}
</style>
