<script setup lang="ts">
import { h, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import {
  NDropdown, NButton, NAvatar, NBadge, NIcon, NPopover,
} from 'naive-ui'
import { Search, LogIn, LogOut, Add, Heart, Notifications } from '@vicons/ionicons5'
import type { Component } from 'vue'
import type { Notification } from '@/types'
import api from '@/api'
import ThemeToggle from './ThemeToggle.vue'

const router = useRouter()
const auth = useAuthStore()
const theme = useThemeStore()


const showSearch = ref(false)
const searchQuery = ref('')

const showNotifs = ref(false)
const notifs = ref<Notification[]>([])
const notifLoading = ref(false)

async function fetchNotifs() {
  if (!auth.isLoggedIn) return
  notifLoading.value = true
  try {
    const { data } = await api.get('/notifications', { params: { page_size: 10 } })
    notifs.value = data.data
  } catch { /* ignore */ } finally {
    notifLoading.value = false
  }
}

async function markRead(notifId: number) {
  try {
    await api.post(`/notifications/${notifId}/read`)
    const n = notifs.value.find(x => x.id === notifId)
    if (n) n.is_read = true
    if (auth.user) auth.user.unread_count = Math.max(0, (auth.user.unread_count || 0) - 1)
  } catch { /* ignore */ }
}

function goNotif(notif: Notification) {
  markRead(notif.id)
  showNotifs.value = false
  if (notif.seed_id) router.push(`/seed/${notif.seed_id}`)
}

function doSearch() {
  if (searchQuery.value.trim()) {
    router.push({ path: '/browse', query: { q: searchQuery.value.trim() } })
    showSearch.value = false
    searchQuery.value = ''
  }
}

function renderIcon(icon: Component) {
  return () => h(NIcon, null, { default: () => h(icon) })
}

const userMenuOptions = [
  { label: '我的投稿', key: 'seeds', icon: renderIcon(Add) },
  { label: '我赞过的', key: 'likes', icon: renderIcon(Heart) },
  { type: 'divider' as const, key: 'd1' },
  { label: '退出登录', key: 'logout', icon: renderIcon(LogOut) },
]

function handleUserSelect(key: string) {
  switch (key) {
    case 'seeds': if (auth.user) router.push(`/user/${auth.user.id}`); break
    case 'likes': if (auth.user) router.push(`/user/${auth.user.id}`); break
    case 'logout': auth.logout(); router.push('/'); break
  }
}
</script>

<template>
  <header class="navbar">
    <div class="navbar-inner">
      <div class="nav-left">
        <router-link to="/" class="nav-logo">
          <img class="nav-logo-icon" src="/logo-44.png" srcset="/logo-22.png 1x, /logo-44.png 2x" width="22" height="22" alt="" />
          <span class="logo-text">Seed Vault</span>
        </router-link>
      </div>
      <div class="nav-center">
        <router-link to="/browse" class="nav-link">浏览</router-link>
        <router-link to="/submit" class="nav-link">投稿</router-link>
        <router-link to="/collections" class="nav-link">收藏夹</router-link>
        <router-link v-if="auth.isAdmin" to="/admin" class="nav-link">审核</router-link>
      </div>
      <div class="nav-right">
        <n-popover
          v-if="auth.isLoggedIn"
          v-model:show="showNotifs"
          trigger="click"
          placement="bottom-end"
          @update:show="(val: boolean) => val && fetchNotifs()"
        >
          <template #trigger>
            <n-badge :value="auth.user?.unread_count" :max="99" :show="(auth.user?.unread_count ?? 0) > 0">
              <n-button quaternary circle size="medium">
                <template #icon><n-icon :component="Notifications" /></template>
              </n-button>
            </n-badge>
          </template>
          <div class="notif-popup">
            <div class="notif-head">通知</div>
            <div v-if="notifs.length === 0" class="notif-empty">暂无通知</div>
            <div
              v-for="n in notifs" :key="n.id"
              class="notif-item"
              :class="{ 'notif-unread': !n.is_read }"
              @click="goNotif(n)"
            >
              <div class="notif-msg">{{ n.message }}</div>
              <div v-if="n.detail" class="notif-detail">{{ n.detail }}</div>
              <div class="notif-time">{{ new Date(n.created_at).toLocaleDateString('zh-CN') }}</div>
            </div>
          </div>
        </n-popover>

        <ThemeToggle />
        <n-popover v-model:show="showSearch" trigger="click" placement="bottom-end">
          <template #trigger>
            <n-button quaternary circle size="medium">
              <template #icon><n-icon :component="Search" /></template>
            </n-button>
          </template>
          <div class="search-popup">
            <input
              v-model="searchQuery"
              class="search-input"
              placeholder="搜索种子标题或描述..."
              @keyup.enter="doSearch"
            />
            <n-button size="small" type="primary" @click="doSearch">搜索</n-button>
          </div>
        </n-popover>

        <template v-if="auth.isLoggedIn && auth.user">
          <n-dropdown trigger="click" :options="userMenuOptions" @select="handleUserSelect">
            <n-badge :value="auth.user.unread_count" :max="99" :show="auth.user.unread_count > 0">
              <n-avatar
                :size="32"
                :src="auth.user.avatar_url"
                :style="{ borderRadius: '4px', cursor: 'pointer' }"
                fallback-src=""
              >
                {{ auth.user.display_name[0] }}
              </n-avatar>
            </n-badge>
          </n-dropdown>
        </template>
        <template v-else>
          <router-link to="/login">
            <n-button size="small" secondary>
              <template #icon><n-icon :component="LogIn" /></template>
              登录
            </n-button>
          </router-link>
        </template>
      </div>
    </div>
  </header>
</template>

<style scoped>
.navbar {
  position: sticky; top: 0; z-index: 100;
  background: var(--paper);
  border-bottom: 2px solid var(--border);
}
.navbar-inner {
  max-width: 1280px; margin: 0 auto; padding: 0 24px;
  height: 56px; display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
}
.nav-left { display: flex; align-items: center; }
.nav-logo {
  display: flex; align-items: center; gap: 10px; text-decoration: none;
  font-family: var(--font-macro); font-size: 1.1rem; font-weight: 800;
  text-transform: uppercase; letter-spacing: 0.04em; color: var(--ink);
}
.nav-logo-icon { display: block; flex-shrink: 0; }
[data-theme="dark"] .nav-logo-icon { filter: invert(1); }
.nav-center {
  display: flex; gap: 0;
  border: 1px solid var(--border);
}
.nav-link {
  padding: 7px 18px; text-decoration: none;
  font-family: var(--font-micro); font-size: 0.7rem; text-transform: uppercase;
  letter-spacing: 0.08em; color: var(--ink);
  border-right: 1px solid var(--border);
  transition: background 80ms, color 80ms;
}
.nav-link::before { content: '[ '; }
.nav-link::after  { content: ' ]'; }
.nav-link:last-child { border-right: none; }
.nav-link:hover, .nav-link.router-link-active { background: var(--ink); color: var(--paper); }
.nav-right { display: flex; align-items: center; justify-content: flex-end; gap: 12px; }
.search-popup { display: flex; gap: 8px; padding: 8px; }
.search-input {
  border: 1px solid var(--border); padding: 6px 12px;
  width: 260px; font-size: 0.75rem; outline: none;
  background: var(--paper); color: var(--ink);
  font-family: var(--font-micro); letter-spacing: 0.04em;
}
.search-input:focus { border-width: 2px; padding: 5px 11px; }
.search-input::placeholder { color: var(--ink-faint); }

.notif-popup { width: 320px; max-height: 420px; overflow-y: auto; }
.notif-head {
  font-family: var(--font-micro); font-size: 0.65rem; font-weight: 500;
  text-transform: uppercase; letter-spacing: 0.1em;
  padding: 10px 14px; border-bottom: 1px solid var(--border);
  color: var(--ink-dim);
}
.notif-empty {
  font-family: var(--font-micro); font-size: 0.7rem; color: var(--ink-dim);
  text-align: center; padding: 24px 14px;
}
.notif-item {
  padding: 10px 14px; cursor: pointer;
  border-bottom: 1px solid var(--ink-faint);
  transition: background 80ms;
}
.notif-item:hover { background: var(--ink-faint); }
.notif-unread { border-left: 2px solid var(--ink); }
.notif-msg {
  font-family: var(--font-micro); font-size: 0.7rem; line-height: 1.4;
}
.notif-detail {
  font-family: var(--font-micro); font-size: 0.65rem; color: var(--ink-dim);
  margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.notif-time {
  font-family: var(--font-micro); font-size: 0.6rem; color: var(--ink-dim);
  margin-top: 4px;
}
</style>
