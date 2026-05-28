<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { darkTheme } from 'naive-ui'
import { useAuthStore } from './stores/auth'
import { useMetaStore } from './stores/meta'
import { useThemeStore } from './stores/theme'
import AppNavbar from './components/AppNavbar.vue'

const auth = useAuthStore()
const meta = useMetaStore()
const theme = useThemeStore()

onMounted(async () => {
  await auth.fetchMe()
  meta.fetchTags()
  meta.fetchVersions()
})

const naiveTheme = computed(() => (theme.isDark ? darkTheme : null))
</script>

<template>
  <n-config-provider :theme="naiveTheme" :theme-overrides="themeOverrides">
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
  background: var(--color-bg-page);
  color: var(--color-text-body);
  -webkit-font-smoothing: antialiased;
  transition: background-color 150ms ease-out, color 150ms ease-out;
}
.app-shell { min-height: 100vh; display: flex; flex-direction: column; }
.app-main { flex: 1; max-width: 1152px; margin: 0 auto; padding: 24px 24px 64px; width: 100%; }
.app-footer {
  text-align: center; padding: 24px; font-size: 13px; color: var(--color-text-muted);
  border-top: 1px solid var(--color-border);
}
.app-footer a { color: var(--color-text-secondary); text-decoration: none; }
.app-footer a:hover { color: var(--color-primary); }
.footer-sep { margin: 0 8px; }
</style>
