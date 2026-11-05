<script setup lang="ts">
/**
 * 审计与留痕提示（NFR-009）。
 *
 * 管理端**全部写操作**的确认环节都必须出现这段提示：NFR-009 要求管理员的关键操作
 * （座位资源状态调整、手动违约登记、黑名单变更、投诉处理、批量取消）留存
 * 「操作者、时间与原因」，因此界面在提交前先告知用户这条操作会被记入审计日志，
 * 并要求填写原因（由各页面的表单 / 抽屉负责校验）。
 */
withDefaults(
  defineProps<{
    /** 操作范围说明（来自 useAdminScope().scopeLabel） */
    scope?: string
    /** 该操作是否要求必填原因 */
    reasonRequired?: boolean
    /** 追加的业务提示（如 BR-019 的保留口径） */
    extra?: string
    type?: 'info' | 'warning'
    /** 是否显示提示标题 */
    title?: string
  }>(),
  { scope: '', reasonRequired: true, extra: '', type: 'info', title: '审计与留痕提示' },
)
</script>

<template>
  <el-alert class="audit" :type="type" :closable="false" show-icon :title="title">
    <p class="audit__line">
      本次操作将记入审计日志：记录操作者、操作时间与原因，保留 1 年，且不提供导出。
    </p>
    <p v-if="scope" class="audit__line">操作范围：{{ scope }}</p>
    <p v-if="reasonRequired" class="audit__line">
      原因必填：原因将随审计记录一并留存，请写明依据以便事后追溯。
    </p>
    <p v-if="extra" class="audit__line">{{ extra }}</p>
  </el-alert>
</template>

<style scoped>
.audit {
  margin-bottom: 12px;
}

.audit__line {
  margin: 2px 0 0;
  font-size: var(--ssr-font-note);
  line-height: 1.6;
}
</style>
