<script setup lang="ts">
/**
 * 登录 / 注册共用的左右分栏骨架：左侧品牌区，右侧 400px 表单卡。
 * 具体标题、表单与样式由各页面通过默认插槽提供。
 */
import BrandPanel from './BrandPanel.vue'
</script>

<template>
  <div class="auth">
    <BrandPanel class="auth__brand" />

    <section class="auth__panel">
      <div class="auth__card">
        <slot />
      </div>
    </section>
  </div>
</template>

<style scoped>
.auth {
  display: flex;
  min-height: 100%;
  background: var(--ssr-surface);
}

/* 品牌区的视觉样式在 components/auth/BrandPanel.vue；这里只管栅格占位 */
.auth__brand {
  flex: 0 0 60%;
}

/* ---- 右：400px 表单卡 ---- */
.auth__panel {
  display: flex;
  flex: 1 1 40%;
  align-items: flex-start;
  justify-content: center;
  min-width: 0;
  padding: 24px 20px;
  overflow-y: auto;
  background: var(--ssr-surface);
  border-left: 1px solid var(--ssr-line);
}

/* 注册表单比登录表单高：用 auto 外边距实现“有空间时垂直居中、空间不足时可滚动”。 */
.auth__card {
  width: 400px;
  max-width: 100%;
  margin: auto 0;
}

@media (max-width: 900px) {
  .auth__brand {
    display: none;
  }

  .auth__panel {
    flex: 1 1 auto;
    border-left: 0;
  }
}
</style>
