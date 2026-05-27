<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from './stores/auth'
import { useMetaStore } from './stores/meta'
import AppNavbar from './components/AppNavbar.vue'

const auth = useAuthStore()
const meta = useMetaStore()

onMounted(async () => {
  await auth.fetchMe()
  meta.fetchTags()
  meta.fetchVersions()
})
</script>

<template>
  <n-config-provider :theme-overrides="themeOverrides">
    <n-message-provider>
      <div class="app-shell">
        <AppNavbar />
        <main class="app-main">
          <router-view />
        </main>
        <footer class="app-footer">
          <span>Seed Vault · 灵感来自斯瓦尔巴全球种子库</span>
          <span class="footer-sep">·</span>
          <a href="https://github.com" target="_blank">GitHub 开源</a>
        </footer>
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<script lang="ts">
const themeOverrides = {
  common: {
    primaryColor: '#3b82f6',
    primaryColorHover: '#2563eb',
    primaryColorPressed: '#1d4ed8',
  },
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
  background: #fafbfc;
  color: #4b5563;
  -webkit-font-smoothing: antialiased;
}
.app-shell { min-height: 100vh; display: flex; flex-direction: column; }
.app-main { flex: 1; max-width: 1152px; margin: 0 auto; padding: 24px 24px 64px; width: 100%; }
.app-footer {
  text-align: center; padding: 24px; font-size: 13px; color: #9ca3af;
  border-top: 1px solid #e4e7eb;
}
.app-footer a { color: #6b7280; text-decoration: none; }
.app-footer a:hover { color: #3b82f6; }
.footer-sep { margin: 0 8px; }
</style>
