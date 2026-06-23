<template>
  <div class="async-loading">
    <a-spin size="large" :tip="tip" />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  tip?: string
}>()
</script>

<style scoped>
.async-loading {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
  background: #fff;
}
</style>
