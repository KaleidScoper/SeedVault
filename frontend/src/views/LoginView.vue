<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NDivider, NSelect, NIcon } from 'naive-ui'
import { LogoMicrosoft } from '@vicons/ionicons5'
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
        <template #icon><n-icon :component="LogoMicrosoft" /></template>
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
  width: 420px; background: var(--paper);
  border: 2px solid var(--border); padding: 40px;
}
h1 {
  font-family: var(--font-macro); font-size: 1.4rem; font-weight: 800;
  text-transform: uppercase; text-align: center;
  margin-bottom: 8px; color: var(--ink);
}
.subtitle {
  text-align: center;
  font-family: var(--font-micro); font-size: 0.7rem;
  color: var(--ink-dim); margin-bottom: 32px;
  letter-spacing: 0.04em;
}
.dev-section { margin-top: 8px; }
.dev-label {
  font-family: var(--font-micro); font-size: 0.6rem;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--ink-dim); margin-bottom: 8px; text-align: center;
}
.dev-row { display: flex; gap: 8px; }
</style>
