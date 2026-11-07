<script setup lang="ts">
/**
 * 管理员个人资料（B1）。
 *
 * 业务管理员 R-02 与系统管理员 R-04 共用：查看本人身份信息、修改联系方式、
 * 修改登录密码。姓名 / 工号 / 角色只读；账户状态由违约或管理员处理变更。
 */
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'

import PasswordChangeDialog from '@/components/account/PasswordChangeDialog.vue'
import PageHeader from '@/components/PageHeader.vue'
import StatusTag from '@/components/StatusTag.vue'
import { updateMyProfile } from '@/api/user'
import { useAuthStore } from '@/stores/auth'
import { toBookingFailure } from '@/utils/bookingData'
import type { BookingFailure } from '@/utils/bookingRules'

const auth = useAuthStore()

const loading = ref(true)
const error = ref<BookingFailure | null>(null)
const editing = ref(false)
const saving = ref(false)
const contactDraft = ref('')
const passwordVisible = ref(false)

const profile = computed(() => auth.user)
const contactText = computed(() => profile.value?.contact?.trim() || '未填写')
const accountStatus = computed(() => profile.value?.account_status ?? '—')

/** 系统管理员本版无业务操作权限，提示语与业务管理员区分 */
const roleHint = computed(() =>
  auth.isSystemAdmin
    ? '系统管理员本版无业务操作权限，仅可维护本人资料。'
    : '管理员可维护自习室、预约、违约、投诉、用户与黑名单；不可修改用户身份信息。',
)

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
    ElMessage.warning('联系方式不能超过 100 字')
    return
  }
  saving.value = true
  try {
    await updateMyProfile({ contact: next })
    await auth.fetchMe()
    ElMessage.success('联系方式已保存')
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
      subtitle="查看管理员资料，修改联系方式与登录密码"
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
          <h3>基本信息</h3>
          <span class="ssr-text-muted">姓名、工号与角色由学校统一维护</span>
        </header>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="姓名">{{ profile.name }}</el-descriptions-item>
          <el-descriptions-item label="学号 / 工号">{{ profile.student_no }}</el-descriptions-item>
          <el-descriptions-item label="角色">{{ profile.role }}</el-descriptions-item>
          <el-descriptions-item label="账户状态">
            <StatusTag kind="account" :value="accountStatus" size="default" />
          </el-descriptions-item>
          <el-descriptions-item label="用户编号">#{{ profile.id }}</el-descriptions-item>
        </el-descriptions>

        <p class="ssr-text-muted note">{{ roleHint }}</p>
      </section>

      <section class="ssr-card block">
        <header class="ssr-card__head">
          <h3>联系方式（可自行修改）</h3>
          <span class="ssr-text-muted">保存后立即生效</span>
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

        <p class="ssr-text-muted note">联系方式仅用于管理员必要时联系你，不会向其他用户展示。</p>
      </section>

      <section class="ssr-card block">
        <header class="ssr-card__head">
          <h3>账户与安全</h3>
          <span class="ssr-text-muted">账户状态 · 登录密码</span>
        </header>

        <dl class="security">
          <div>
            <dt>账户状态</dt>
            <dd>
              <StatusTag kind="account" :value="accountStatus" />
              <span v-if="accountStatus === '停用'">停用账户无法登录，须由管理员恢复。</span>
              <span v-else>当前账户可正常登录管理端。</span>
            </dd>
          </div>
          <div>
            <dt>修改密码</dt>
            <dd>
              <el-button size="small" @click="passwordVisible = true">修改密码</el-button>
              <span class="ssr-text-muted">
                需验证原密码；修改后其他设备需重新登录。
              </span>
            </dd>
          </div>
        </dl>
      </section>
    </template>

    <div v-else class="ssr-card block">
      <el-empty description="未取得用户信息，请重新登录后再试" />
    </div>

    <PasswordChangeDialog v-model="passwordVisible" />
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



