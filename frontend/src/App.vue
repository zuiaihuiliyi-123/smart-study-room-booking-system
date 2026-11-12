<script setup lang="ts">
import AppErrorBoundary from '@/components/AppErrorBoundary.vue'
import OfflineBanner from '@/components/OfflineBanner.vue'
</script>

<template>
  <OfflineBanner />
  <AppErrorBoundary>
    <router-view />
  </AppErrorBoundary>
</template>
