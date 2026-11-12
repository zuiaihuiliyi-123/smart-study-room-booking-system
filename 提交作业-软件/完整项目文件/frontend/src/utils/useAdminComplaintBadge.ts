/**
 * 管理端「待处理投诉」角标（A3 轻量方案）。
 *
 * 不引入管理员站内消息页：只把“待处理投诉数”显示在侧栏「投诉处理」菜单上，
 * 让管理员登录后能直接看到是否有新投诉需要处理。
 *
 * 口径：
 * - 只统计 `status=待处理`，与投诉处理页默认队列一致；
 * - 后台轮询，失败静默（`silent: true`），不刷 toast、不影响业务页面；
 * - 页面隐藏时暂停请求，恢复可见或路由切换时立即刷新；
 * - 投诉处理成功后由 `useComplaintManage` 派发 `ssr:complaints-changed`，角标立即更新。
 */
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { listAllComplaints } from '@/api/complaint'
import { useAuthStore } from '@/stores/auth'

/** 后台轮询周期：投诉提醒不要求秒级实时 */
export const PENDING_COMPLAINT_REFRESH_MS = 60_000

export function useAdminComplaintBadge() {
  const auth = useAuthStore()
  const route = useRoute()

  const pendingCount = ref(0)
  let timer: number | null = null
  let inFlight = false

  async function refresh(): Promise<void> {
    if (!auth.isAdmin || inFlight) return
    // 页面隐藏时跳过后台轮询；恢复可见由 visibilitychange 立即补一次
    if (document.visibilityState === 'hidden') return
    inFlight = true
    try {
      const result = await listAllComplaints(
        { status: '待处理', page: 1, page_size: 1 },
        { silent: true },
      )
      pendingCount.value = result.total
    } catch {
      // 角标是辅助信息：失败保留上一次值，不弹提示
    } finally {
      inFlight = false
    }
  }

  function stopTimer(): void {
    if (timer !== null) {
      window.clearInterval(timer)
      timer = null
    }
  }

  function startTimer(): void {
    stopTimer()
    timer = window.setInterval(() => {
      void refresh()
    }, PENDING_COMPLAINT_REFRESH_MS)
  }

  function onVisibilityChange(): void {
    if (document.visibilityState === 'visible') void refresh()
  }

  function onComplaintsChanged(): void {
    void refresh()
  }

  onMounted(() => {
    document.addEventListener('visibilitychange', onVisibilityChange)
    window.addEventListener('ssr:complaints-changed', onComplaintsChanged)
    if (auth.isAdmin) {
      void refresh()
      startTimer()
    }
  })

  // 登录态变化（例如刷新后用户信息稍后到达）时启动或停止轮询
  watch(
    () => auth.isAdmin,
    (isAdmin) => {
      if (isAdmin) {
        void refresh()
        startTimer()
      } else {
        stopTimer()
        pendingCount.value = 0
      }
    },
  )

  // 管理端页面切换时刷新，避免必须等 60 秒
  watch(
    () => route.path,
    () => {
      if (auth.isAdmin) void refresh()
    },
  )

  onBeforeUnmount(() => {
    stopTimer()
    document.removeEventListener('visibilitychange', onVisibilityChange)
    window.removeEventListener('ssr:complaints-changed', onComplaintsChanged)
  })

  const badges = computed<Record<string, number>>(() => {
    const result: Record<string, number> = {}
    if (auth.isAdmin && pendingCount.value > 0) {
      result['/admin/complaints'] = pendingCount.value
    }
    return result
  })

  return { pendingCount, badges, refresh }
}
