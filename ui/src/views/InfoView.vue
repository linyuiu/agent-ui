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

<style scoped>
.info-view {
  display: grid;
  gap: 16px;
}

.panel {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 18px;
  padding: 24px;
  border: 1px solid rgba(15, 40, 55, 0.06);
}

.panel-header h2 {
  margin: 0 0 6px;
  font-family: 'Space Grotesk', sans-serif;
  font-size: 24px;
}

.panel-header p {
  margin: 0;
  color: #5b6b71;
}

.panel-body {
  margin-top: 18px;
}

.placeholder {
  display: flex;
  gap: 16px;
  align-items: center;
  padding: 18px;
  border-radius: 14px;
  background: rgba(15, 179, 185, 0.08);
  border: 1px dashed rgba(15, 179, 185, 0.2);
}

.placeholder-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: linear-gradient(120deg, #0fb3b9, #5ce1e6);
}

.placeholder h3 {
  margin: 0 0 4px;
  font-size: 16px;
}

.placeholder p {
  margin: 0;
  color: #4a5a60;
  font-size: 13px;
}
</style>
