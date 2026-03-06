<template>
  <div v-if="open" class="modal-backdrop">
    <div class="modal-card">
      <div class="modal-header">
        <h3>{{ title }}</h3>
        <button class="modal-close" type="button" @click="$emit('close')">✕</button>
      </div>
      <p class="modal-body">{{ message }}</p>
      <div class="modal-actions">
        <button class="ghost" type="button" @click="$emit('close')">{{ cancelText }}</button>
        <button v-if="secondaryText" class="ghost" type="button" @click="$emit('secondary')">
          {{ secondaryText }}
        </button>
        <button class="primary" type="button" :disabled="loading" @click="$emit('confirm')">
          {{ loading ? loadingText : confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    open: boolean
    title: string
    message: string
    loading?: boolean
    confirmText?: string
    cancelText?: string
    secondaryText?: string
    loadingText?: string
  }>(),
  {
    loading: false,
    confirmText: '确认',
    cancelText: '取消',
    secondaryText: '',
    loadingText: '处理中...',
  }
)

defineEmits<{
  (event: 'close'): void
  (event: 'secondary'): void
  (event: 'confirm'): void
}>()
</script>

<style scoped src="./ConfirmDialog.css"></style>
