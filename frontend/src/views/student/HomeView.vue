<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Calendar, Tickets, Warning } from '@element-plus/icons-vue'

import { checkIn, checkOut } from '@/api/reservation'
import MessageDigest from '@/components/home/MessageDigest.vue'
import TodayReservationCard from '@/components/home/TodayReservationCard.vue'
import { useAuthStore } from '@/stores/auth'
import { useMessageStore } from '@/stores/message'
import type { Reservation, StationMessage } from '@/types'
import {
  fetchAllMyReservations,
  loadSeatDirectory,
  toBookingFailure,
  type SeatRef,
} from '@/utils/bookingData'
import { isEffectiveReservation, parseTimeToMinutes, todayText, todayIso } from '@/utils/bookingRules'
import type { BookingFailure } from '@/utils/bookingRules'
import { relatedRoute } from '@/utils/messageLinks'
import { useClock } from '@/utils/useClock'

const router = useRouter()
const auth = useAuthStore()
const clock = useClock()
const messages = useMessageStore()

const directory = ref<Map<number, SeatRef> | null>(null)
const myReservations = ref<Reservation[]>([])
const loading = ref(true)
const error = ref<BookingFailure | null>(null)

const today = computed(() => todayIso(clock.value))
const greetingDate = computed(() => todayText(clock.value))

/** 今日有效预约（待使用 / 使用中），按开始时间升序 */
const todayReservations = computed(() =>
    myReservations.value
    .filter((item) => item.reserve_date === today.value && isEffectiveReservation(item))
    .sort((a, b) => (parseTimeToMinutes(a.start_time) ?? 0) - (parseTimeToMinutes(b.start_time) ?? 0)),
)

const entries = [
  { title: '预约座位', description: '查询可预约座位并提交预约', to: '/student/booking', icon: Calendar },
  { title: '我的预约', description: '查看预约、签到与签退', to: '/student/reservations', icon: Tickets },
  { title: '我的违约', description: '查看违约记录与账户状态', to: '/student/violations', icon: Warning },
]

async function load() {
  loading.value = true
  error.value = null
  try {
    myReservations.value = await fetchAllMyReservations()
  } catch (caught) {
    error.value = toBookingFailure(caught)
  } finally {
    loading.value = false
  }
  // 座位目录只用于把 seat_id 展示成「自习室 · A-01」；失败时退化为「座位 #id」，不影响主流程
  if (directory.value === null) {
    directory.value = await loadSeatDirectory().catch(() => null)
  }
}

/** 站内消息来自 store（与顶栏角标、消息页同一份数据），首次加载由布局触发，此处不重复请求。 */
async function loadMessages(force = false) {
  await messages.load(force)
}

async function onCheckIn(reservation: Reservation) {
  try {
    const result = await checkIn(reservation.id)
    ElMessage.success(result.message)
    await Promise.all([load(), loadMessages(true)])
  } catch {
    // 失败提示由 request.ts 拦截器统一用 ElMessage 呈现，已选条件不受影响
  }
}

async function onCheckOut(reservation: Reservation) {
  try {
    const result = await checkOut(reservation.id)
    ElMessage.success(result.message)
    await Promise.all([load(), loadMessages(true)])
  } catch {
    // 同上
  }
}

async function onOpenMessage(message: StationMessage) {
  const target = relatedRoute(message)
  if (!message.is_read) {
    try {
      await messages.markRead(message.id)
    } catch {
      return
    }
  }
  if (target) {
    void router.push(target)
  } else {
    ElMessage.info('该消息没有关联对象，已标记为已读')
  }
}

onMounted(() => {
  void auth.fetchMe().catch(() => undefined)
  void load()
  void loadMessages()
})
</script>

<template>
  <div class="page home-page">
    <section class="welcome">
      <svg class="welcome__mark" viewBox="0 0 32 32" aria-hidden="true" focusable="false">
        <rect x="1" y="1" width="30" height="30" rx="8" fill="none" stroke="currentColor" stroke-width="2" />
        <rect x="7" y="9" width="18" height="3" rx="1.5" fill="currentColor" />
        <rect x="8" y="15" width="5" height="8" rx="1.5" fill="currentColor" />
        <rect x="19" y="15" width="5" height="8" rx="1.5" fill="currentColor" />
      </svg>
      <div class="welcome__text">
        <h2>你好，{{ auth.user?.name ?? '同学' }}</h2>
        <p>
          今天是 {{ greetingDate }} · 账户状态
          <strong>{{ auth.user?.account_status ?? '—' }}</strong> · 累计违约
            <strong>{{ auth.user?.violation_count ?? 0 }}</strong> 次
            <span class="ssr-text-muted">（违约满 3 次触发 7 天限制）</span>
          </p>
        </div>
        <el-button type="primary" @click="router.push('/student/booking')">预约座位</el-button>
      </section>

      <div class="home-grid">
        <div class="home-col">
          <TodayReservationCard
            :reservations="todayReservations"
            :directory="directory"
            :now="clock"
            :loading="loading"
            :error-message="error?.message ?? ''"
            @checkin="onCheckIn"
            @checkout="onCheckOut"
            @retry="load"
            @booking="router.push('/student/booking')"
          />

          <section class="entries" aria-label="快捷入口">
            <button
              v-for="entry in entries"
              :key="entry.to"
              class="entry"
              type="button"
              @click="router.push(entry.to)"
            >
              <el-icon class="entry__icon"><component :is="entry.icon" /></el-icon>
              <span class="entry__title">{{ entry.title }}</span>
              <span class="entry__desc">{{ entry.description }}</span>
            </button>
          </section>
        </div>

        <MessageDigest
          :messages="messages.unreadItems.slice(0, 3)"
          :unread-total="messages.unreadCount"
          :loading="messages.loading"
          :error-message="messages.errorMessage"
          @open="onOpenMessage"
          @retry="loadMessages(true)"
        />
      </div>
    </div>
</template>

<style scoped>
.welcome {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
  padding: 16px 18px;
  margin-bottom: 16px;
  color: var(--ssr-on-primary);
  background: linear-gradient(120deg, var(--ssr-primary), var(--ssr-primary-deep));
  border-radius: var(--ssr-radius);
}

.welcome__mark {
  flex: 0 0 auto;
  width: 34px;
  height: 34px;
}

.welcome__text {
  flex: 1 1 260px;
  min-width: 0;
}

.welcome__text h2 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
}

.welcome__text p {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 6px;
  align-items: baseline;
  margin: 5px 0 0;
  font-size: var(--ssr-font-note);
}

.welcome__text .ssr-text-muted {
  color: rgb(255 255 255 / 82%);
}

.home-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(0, 1fr);
  gap: 16px;
  align-items: start;
}

.home-col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

.entries {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
}

.entry {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
  padding: 14px 16px;
  font-family: inherit;
  text-align: left;
  background: var(--ssr-surface);
  border: 1px solid var(--ssr-line);
  border-radius: var(--ssr-radius);
  cursor: pointer;
}

.entry:hover {
  border-color: var(--ssr-primary);
}

.entry__icon {
  color: var(--ssr-primary);
  font-size: 18px;
}

.entry__title {
  font-size: 14px;
  font-weight: 600;
}

.entry__desc {
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

@media (max-width: 1024px) {
  .home-grid {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
