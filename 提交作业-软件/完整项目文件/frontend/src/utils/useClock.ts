import { onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

/**
 * 每秒跳动的时钟，用于签到倒计时等展示。
 *
 * 注意：这是**本机时钟**。签到窗口是否命中由服务端按服务器时间判定（NFR-010），
 * 因此界面上的倒计时只是估算，最终以服务端返回的窗口与判定结果为准。
 */
export function useClock(intervalMs = 1000): Ref<Date> {
  const now = ref(new Date())
  let timer: number | null = null

  onMounted(() => {
    timer = window.setInterval(() => {
      now.value = new Date()
    }, intervalMs)
})

onBeforeUnmount(() => {
  if (timer !== null) window.clearInterval(timer)
  timer = null
})

return now
}
