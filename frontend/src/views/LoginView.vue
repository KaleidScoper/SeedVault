<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NDivider, NSelect, NIcon } from 'naive-ui'
import { LogIn } from '@vicons/ionicons5'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const router = useRouter()
const auth = useAuthStore()
const devUserId = ref(1)
const devUsers = [
  { label: 'Kaleid_5coper (Admin)', value: 1 },
  { label: '方块猎人 (Player)', value: 2 },
  { label: '建筑大师 (Player)', value: 3 },
  { label: '速通玩家 (Player)', value: 4 },
]

async function msLogin() {
  window.location.href = '/api/v1/auth/login'
}

async function doDevLogin() {
  await auth.devLogin(devUserId.value)
  router.push('/')
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1>登录 Seed Vault</h1>
      <p class="subtitle">使用 Microsoft 账号登录，自动创建账户</p>

      <n-button block size="large" @click="msLogin" style="height:44px">
        <template #icon><n-icon :component="LogIn" /></template>
        使用 Microsoft 账号登录
      </n-button>

      <n-divider />

      <div class="dev-section">
        <p class="dev-label">开发模式登录</p>
        <div class="dev-row">
          <n-select v-model:value="devUserId" :options="devUsers" size="small" style="flex:1" />
          <n-button size="small" type="primary" @click="doDevLogin">登录</n-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex; align-items: center; justify-content: center;
  min-height: 60vh;
}
.login-card {
  width: 400px; background: #fff; border: 1px solid #e4e7eb;
  border-radius: 8px; padding: 40px;
}
h1 { font-size: 22px; font-weight: 600; text-align: center; margin-bottom: 8px; color: #1f2937; }
.subtitle { text-align: center; font-size: 14px; color: #9ca3af; margin-bottom: 32px; }
.dev-section { margin-top: 8px; }
.dev-label { font-size: 12px; color: #9ca3af; margin-bottom: 8px; text-align: center; }
.dev-row { display: flex; gap: 8px; }
</style>
