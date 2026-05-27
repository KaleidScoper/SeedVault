<script setup lang="ts">
import { h, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  NDropdown, NButton, NAvatar, NBadge, NIcon, NPopover,
} from 'naive-ui'
import { Diamond, Search, LogIn, LogOut, Add, FolderOpen, ShieldCheckmark, Heart } from '@vicons/ionicons5'
import type { Component } from 'vue'

const router = useRouter()
const auth = useAuthStore()

const showSearch = ref(false)
const searchQuery = ref('')

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
  { label: '收藏夹', key: 'collections', icon: renderIcon(FolderOpen) },
  ...(auth.isAdmin ? [{ label: '管理后台', key: 'admin', icon: renderIcon(ShieldCheckmark) }] : []),
  { type: 'divider' as const, key: 'd1' },
  { label: '退出登录', key: 'logout', icon: renderIcon(LogOut) },
]

function handleUserSelect(key: string) {
  switch (key) {
    case 'seeds': router.push('/browse?my=1'); break
    case 'likes': router.push('/browse?liked=1'); break
    case 'collections': router.push('/collections'); break
    case 'admin': router.push('/admin'); break
    case 'logout': auth.logout(); router.push('/'); break
  }
}
</script>

<template>
  <header class="navbar">
    <div class="navbar-inner">
      <div class="nav-left">
        <router-link to="/" class="nav-logo">
          <n-icon size="22" :component="Diamond" color="#3b82f6" />
          <span class="logo-text">Seed Vault</span>
        </router-link>
      </div>
      <div class="nav-center">
        <router-link to="/browse" class="nav-link">浏览</router-link>
        <router-link to="/submit" class="nav-link">投稿</router-link>
      </div>
      <div class="nav-right">
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
  background: rgba(250,251,252,0.92); backdrop-filter: blur(8px);
  border-bottom: 1px solid #e4e7eb;
}
.navbar-inner {
  max-width: 1152px; margin: 0 auto; padding: 0 24px;
  height: 56px; display: flex; align-items: center; gap: 32px;
}
.nav-left { display: flex; align-items: center; }
.nav-logo {
  display: flex; align-items: center; gap: 8px; text-decoration: none;
  font-size: 18px; font-weight: 600; color: #1f2937; letter-spacing: 0.04em;
}
.nav-center { display: flex; gap: 4px; }
.nav-link {
  padding: 6px 16px; border-radius: 6px; text-decoration: none;
  font-size: 15px; color: #4b5563; transition: background 150ms;
}
.nav-link:hover, .nav-link.router-link-active { background: #eff6ff; color: #3b82f6; }
.nav-right { margin-left: auto; display: flex; align-items: center; gap: 12px; }
.search-popup { display: flex; gap: 8px; padding: 8px; }
.search-input {
  border: 1px solid #e4e7eb; border-radius: 6px; padding: 6px 12px;
  width: 260px; font-size: 14px; outline: none;
}
.search-input:focus { border-color: #3b82f6; }
</style>
