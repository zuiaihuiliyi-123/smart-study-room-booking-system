<script setup lang="ts">
/**
 * 站内消息列表（FR-060）。
 *
 * 分页与类型筛选**都由服务端完成**（`GET /messages/me?page=&type=`），
 * 因此消息量超过 500 条时不会像旧实现那样被静默截断。
 * 未读数来自 `GET /messages/unread-count`，与当前分页解耦。
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'

import MessageList from '@/components/messages/MessageList.vue'
import PageHeader from '@/components/PageHeader.vue'
import { MESSAGE_TYPES, useMessageStore } from '@/stores/message'
import type { StationMessage } from '@/types'
import { relatedRoute } from '@/utils/messageLinks'

const router = useRouter()
const store = useMessageStore()

const markingAll = ref(false)

const emptyText = computed(() =>
  store.type === 'all'
    ? '还没有收到站内消息；预约成功、违约登记、投诉反馈都会在这里提示'
    : `没有「${store.type}」类型的消息`,
)

/** 切换类型：回到第 1 页并重新向服务端取数 */
watch(
  () => store.type,
  () => {
    void store.load(true)
  },
)

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

function onPageChange(next: number): void {
  store.page = next
  void store.load()
}

onMounted(() => {
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
          {{ store.unreadCount }} 条未读 / 共 {{ store.total }} 条
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
        <el-button :loading="store.loading" @click="store.load()">刷新</el-button>
      </template>
    </PageHeader>

    <el-radio-group v-model="store.type" class="types">
      <el-radio-button value="all">全部</el-radio-button>
      <el-radio-button v-for="type in MESSAGE_TYPES" :key="type" :value="type">
        {{ type }}
      </el-radio-button>
    </el-radio-group>

    <MessageList
      :items="store.items"
      :loading="store.loading"
      :error-message="store.errorMessage"
      :empty-text="emptyText"
      @open="onOpen"
      @retry="store.load()"
    />

    <div v-if="!store.loading && !store.errorMessage && store.total > store.pageSize" class="pager">
      <el-pagination
        background
        layout="total, prev, pager, next"
        :total="store.total"
        :current-page="store.page"
        :page-size="store.pageSize"
        @current-change="onPageChange"
      />
    </div>

    <p class="ssr-text-muted note">
      点击消息会标记为已读，并跳转到对应的列表页（列表内会高亮该条记录）。
      列表与类型筛选均由服务端分页处理。
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
