<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import { updateMyProfile } from '@/api/user'
import { useAuthStore } from '@/stores/auth'
import { toBookingFailure } from '@/utils/bookingData'
import { BOOKING_RULES, restrictUntilText, type BookingFailure } from '@/utils/bookingRules'

const auth = useAuthStore()

const loading = ref(true)
const error = ref<BookingFailure | null>(null)
const editing = ref(false)
const saving = ref(false)
const contactDraft = ref('')

const profile = computed(() => auth.user)
const contactText = computed(() => profile.value?.contact?.trim() || '未填写')
const restrictUntil = computed(() => restrictUntilText(profile.value?.restrict_until ?? ''))
const accountStatus = computed(() => profile.value?.account_status ?? '—')

async function load(): Promise<void> {
  loading.value = true
  error.value = null
  try {
    await auth.fetchMe()
  } catch (caught) {
    error.value = toBookingFailure(caught)
  } finally {
    loading.value = false
  }
}

function startEdit(): void {
  contactDraft.value = profile.value?.contact ?? ''
  editing.value = true
}

function cancelEdit(): void {
  editing.value = false
  contactDraft.value = ''
}

async function saveContact(): Promise<void> {
  const next = contactDraft.value.trim()
  if (next.length > 100) {
    ElMessage.warning('联系方式不能超过 100 字（与后端字段约束一致）')
    return
  }
  saving.value = true
  try {
    await updateMyProfile({ contact: next })
    await auth.fetchMe()
    ElMessage.success('联系方式已保存；身份信息（姓名、学号、角色）与账户状态不可自行修改')
    editing.value = false
  } catch {
    // 失败提示由 request.ts 拦截器统一给出，草稿保留便于修正
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<template>
  <div class="page">
    <PageHeader
      title="个人资料"
      subtitle="用户信息管理（身份信息只读，仅联系方式可自行修改）"
    >
      <template #actions>
        <el-button :loading="loading" @click="load">刷新</el-button>
      </template>
    </PageHeader>

    <el-alert
      v-if="error"
      class="block"
      type="error"
      :closable="false"
      show-icon
      title="个人资料读取失败"
    >
      <p>{{ error.message }}</p>
    </el-alert>

    <div v-if="loading" class="ssr-card block">
      <el-skeleton :rows="5" animated />
    </div>

    <template v-else-if="profile">
      <section class="ssr-card block">
        <header class="ssr-card__head">
          <h3>基本信息（只读）</h3>
          <span class="ssr-text-muted">数据来源：GET /users/me（统一身份认证同步，本系统只读入不回写）</span>
        </header>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="姓名">{{ profile.name }}</el-descriptions-item>
          <el-descriptions-item label="学号 / 工号">{{ profile.student_no }}</el-descriptions-item>
          <el-descriptions-item label="角色">{{ profile.role }}</el-descriptions-item>
          <el-descriptions-item label="账户状态">
            <StatusTag kind="account" :value="accountStatus" size="default" />
          </el-descriptions-item>
          <el-descriptions-item label="累计违约次数">
            <router-link class="link" to="/student/violations">
              {{ profile.violation_count }} 次
            </router-link>
            <span class="ssr-text-muted">
              （满 {{ BOOKING_RULES.violationThreshold }} 次限制 {{ BOOKING_RULES.restrictionDays }} 天）
            </span>
          </el-descriptions-item>
          <el-descriptions-item label="用户编号">#{{ profile.id }}</el-descriptions-item>
        </el-descriptions>

        <p class="ssr-text-muted note">
          姓名、学号与角色由统一身份认证同步，本系统只读；与 已裁定管理员亦不可编辑身份信息，
          学生端同样不提供编辑入口。账户状态只能经 的黑名单 / 停用流程变更，不能自助修改。
        </p>
      </section>

      <section class="ssr-card block">
        <header class="ssr-card__head">
          <h3>联系方式（唯一可自行修改的字段）</h3>
          <span class="ssr-text-muted">PATCH /users/me · 无审核</span>
        </header>

        <div v-if="!editing" class="contact">
          <span class="contact__value">{{ contactText }}</span>
          <el-button size="small" @click="startEdit">
            {{ profile.contact ? '修改' : '填写' }}
          </el-button>
        </div>

        <div v-else class="contact">
          <el-input
            v-model="contactDraft"
            class="contact__input"
            maxlength="100"
            show-word-limit
            placeholder="手机号或邮箱，最多 100 字"
          />
          <el-button type="primary" size="small" :loading="saving" @click="saveContact">
            保存
          </el-button>
          <el-button size="small" @click="cancelEdit">取消</el-button>
        </div>

        <p class="ssr-text-muted note">
          本人资料页显示联系方式原值（属于本人数据）；学生端其他列表不展示他人姓名、学号与联系方式
          （个人信息脱敏）。
        </p>
      </section>

      <section class="ssr-card block">
        <header class="ssr-card__head">
          <h3>账户与安全</h3>
          <span class="ssr-text-muted">账户状态 · 口令存储</span>
        </header>

        <dl class="security">
          <div>
            <dt>账户状态</dt>
            <dd>
              <StatusTag kind="account" :value="accountStatus" />
              <span v-if="accountStatus === '受限'">
                受限期间不能创建新预约，既有预约保持原状、可正常签到使用。
              </span>
              <span v-else-if="accountStatus === '停用'">
                停用账户无法登录，须由管理员恢复。
              </span>
              <span v-else>当前不受限，可正常创建预约（每人每日 {{ BOOKING_RULES.dailyLimit }} 条）。</span>
            </dd>
          </div>
          <div v-if="accountStatus === '受限'">
            <dt>预计解除时间</dt>
            <dd>
              <b v-if="restrictUntil">{{ restrictUntil }}</b>
              <span v-else class="ssr-text-muted">待后端提供接口（见下方说明）</span>
            </dd>
          </div>
          <div>
            <dt>修改密码</dt>
            <dd>
              <el-button size="small" disabled>修改密码</el-button>
              <span class="ssr-text-muted">
                待后端提供接口：后端仅有 <code>GET /users/me</code> 与
                <code>PATCH /users/me</code>（只接受 contact），没有口令修改接口；SRS 也未定义口令自助修改流程，
                  因此这里不放假表单，接口就绪后再接入。
                  </span>
                </dd>
              </div>
              <div v-if="accountStatus === '受限'">
                <dt>字段说明</dt>
                <dd class="ssr-text-muted">
                  预计解除时间需要后端补一个学生可读的字段（如 <code>UserRead.restrict_until</code>）；
                  受限于 <code>GET /blacklist</code> 仅管理员可用，前端无法在不新增接口的前提下取到该时间，
                  页面也不会自行推算日期。
                </dd>
              </div>
            </dl>
          </section>
        </template>

        <div v-else class="ssr-card block">
          <el-empty description="未取得用户信息，请重新登录后再试" />
        </div>
      </div>
</template>

<style scoped>
.block {
  margin-bottom: 16px;
}

.note {
  margin: 10px 0 0;
  line-height: 1.7;
}

.link {
  color: var(--ssr-primary);
  font-weight: 600;
}

.contact {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.contact__value {
  font-size: 15px;
  font-weight: 600;
}

.contact__input {
  flex: 1 1 240px;
  max-width: 360px;
}

.security {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin: 0;
}

.security div {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  align-items: baseline;
}

.security dt {
  flex: 0 0 96px;
  color: var(--ssr-muted-ink);
  font-size: var(--ssr-font-note);
}

.security dd {
  flex: 1 1 320px;
  min-width: 0;
  margin: 0;
  font-size: var(--ssr-font-note);
  line-height: 1.7;
}
</style>
