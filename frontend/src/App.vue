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
          <span>SEED VAULT &copy; 2026</span>
          <span class="footer-sep">&#x25AA;</span>
          <span>灵感来自斯瓦尔巴全球种子库</span>
          <span class="footer-sep">&#x25AA;</span>
          <span>REGISTRY ID: SV-NO-0001</span>
        </footer>
      </div>
    </n-message-provider>
  </n-config-provider>
</template>

<script lang="ts">
const themeOverrides = {
  common: {
    primaryColor: '#0A0A0A',
    primaryColorHover: '#E61919',
    primaryColorPressed: '#B81515',
    borderRadius: '0px',
    fontFamily: "'JetBrains Mono', monospace",
  },
  Button: {
    borderRadiusSmall: '0px',
    borderRadiusMedium: '0px',
    borderRadiusLarge: '0px',
  },
  Input: {
    borderRadius: '0px',
  },
  Select: {
    borderRadius: '0px',
  },
  Dropdown: {
    borderRadius: '0px',
  },
  Tag: {
    borderRadius: '0px',
  },
  Card: {
    borderRadius: '0px',
  },
  Modal: {
    borderRadius: '0px',
  },
  Message: {
    borderRadius: '0px',
  },
}
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

html {
  background: var(--paper);
  -webkit-font-smoothing: antialiased;
}

body {
  font-family: var(--font-micro);
  font-size: 0.8rem;
  letter-spacing: 0.04em;
  color: var(--ink);
  background: var(--paper);
}

a { color: var(--ink); }
a:hover { color: var(--red); }

.app-shell { min-height: 100vh; display: flex; flex-direction: column; }
.app-main { flex: 1; max-width: 1280px; margin: 0 auto; padding: 24px 24px 64px; width: 100%; }

.app-footer {
  text-align: center; padding: 20px 24px;
  font-family: var(--font-micro); font-size: 0.65rem;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--ink-dim);
  border-top: 2px solid var(--border);
}
.app-footer .footer-sep { margin: 0 10px; color: var(--ink-faint); }

/* ── Naive UI brutalist normalisation ── */
.n-button { border-radius: 0 !important; }
.n-input { border-radius: 0 !important; }
.n-select { border-radius: 0 !important; }
.n-base-selection, .n-base-selection-label { border-radius: 0 !important; }
.n-dropdown-menu { border-radius: 0 !important; }
.n-tag { border-radius: 0 !important; }
.n-card { border-radius: 0 !important; }
.n-modal-card { border-radius: 0 !important; }
.n-message { border-radius: 0 !important; }
.n-popover { border-radius: 0 !important; }
.n-tooltip { border-radius: 0 !important; }
.n-pagination .n-pagination-item { border-radius: 0 !important; }
</style>
