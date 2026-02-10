<template>
  <div class="info-view">
    <div class="panel">
      <div class="panel-header">
        <h2>{{ title }}</h2>
        <p>{{ description }}</p>
      </div>
      <div class="panel-body">
        <div class="placeholder">
          <div class="placeholder-icon"></div>
          <div>
            <h3>功能建设中</h3>
            <p>该页面已就位，后续将接入具体功能配置。</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const title = computed(() => String(route.meta.title || '系统页面'))
const description = computed(() => String(route.meta.description || ''))
</script>

<style scoped src="./InfoView.css"></style>
