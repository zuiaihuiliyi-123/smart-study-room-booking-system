<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

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
const markingAll = ref(false)

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

async function onMarkAllRead(): Promise<void> {
  const count = store.unreadCount
  if (count === 0) return
  try {
    await ElMessageBox.confirm(
      `将把 ${count} 条未读消息标为已读，标记后不再显示未读提示。`,
      '全部标为已读',
      { confirmButtonText: '标为已读', cancelButtonText: '取消', type: 'info' },
    )
  } catch {
    return
  }

  markingAll.value = true
  try {
    const done = await store.markAllRead()
    ElMessage.success(`已把 ${done} 条消息标为已读`)
  } catch (caught) {
    ElMessage.error(caught instanceof Error ? caught.message : '标记失败，请刷新后重试')
  } finally {
    markingAll.value = false
  }
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
      subtitle="查看系统发送给你的站内消息"
    >
      <template #actions>
        <span class="ssr-text-muted">
          {{ store.unreadCount }} 条未读 / 共 {{ store.items.length }} 条
        </span>
        <el-button
          type="primary"
          plain
          :disabled="store.unreadCount === 0 || store.loading"
          :loading="markingAll"
          @click="onMarkAllRead"
        >
          全部标为已读
        </el-button>
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
</style>
