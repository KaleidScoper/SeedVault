<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { NTag, NIcon, NDivider } from 'naive-ui'
import { CheckmarkCircle } from '@vicons/ionicons5'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'
import type { SeedListItem } from '@/types'
import SeedCard from '@/components/SeedCard.vue'

const route = useRoute()
const auth = useAuthStore()
const userId = computed(() => Number(route.params.id))
const isOwnProfile = computed(() => auth.user?.id === userId.value)

interface UserProfile {
  id: number
  display_name: string
  minecraft_username: string | null
  avatar_url: string | null
  owns_java_edition: boolean
  approved_seed_count: number
  created_at: string
}

const profile = ref<UserProfile | null>(null)
const profileLoading = ref(true)

const activeTab = ref<'seeds' | 'likes'>('seeds')
const seeds = ref<SeedListItem[]>([])
const seedsLoading = ref(false)
const seedsTotal = ref(0)

onMounted(async () => {
  try {
    const { data } = await api.get(`/users/${userId.value}`)
    profile.value = data.data
  } finally {
    profileLoading.value = false
  }
  await fetchSeeds()
})

async function fetchSeeds() {
  seedsLoading.value = true
  try {
    if (activeTab.value === 'likes' && isOwnProfile.value) {
      const { data } = await api.get('/users/me/bookmarks', { params: { page: 1, page_size: 24 } })
      seeds.value = data.data
      seedsTotal.value = data.meta?.total ?? 0
    } else if (activeTab.value === 'seeds' && isOwnProfile.value) {
      const { data } = await api.get('/users/me/seeds', { params: { page: 1, page_size: 24 } })
      seeds.value = data.data
      seedsTotal.value = data.meta?.total ?? 0
    } else {
      const { data } = await api.get('/seeds', { params: { uploader_id: userId.value, page_size: 24 } })
      seeds.value = data.data
      seedsTotal.value = data.meta?.total ?? 0
    }
  } finally {
    seedsLoading.value = false
  }
}

async function switchTab(tab: 'seeds' | 'likes') {
  activeTab.value = tab
  await fetchSeeds()
}

function onSeedUpdated() {
  fetchSeeds()
}
</script>

<template>
  <div v-if="profileLoading" class="loading">加载中...</div>
  <div v-else-if="!profile" class="error">用户不存在</div>
  <div v-else class="user-page container">
    <div class="profile-header">
      <img
        v-if="profile.avatar_url"
        :src="profile.avatar_url"
        class="profile-avatar"
      />
      <div v-else class="profile-avatar-placeholder">{{ profile.display_name[0] }}</div>
      <div class="profile-info">
        <div class="profile-name-row">
          <h1 class="profile-name">{{ profile.display_name }}</h1>
          <n-tag v-if="profile.owns_java_edition" size="tiny" type="success">
            <template #icon><n-icon :component="CheckmarkCircle" /></template>
            正版玩家
          </n-tag>
        </div>
        <p v-if="profile.minecraft_username" class="profile-mc">
          {{ profile.minecraft_username }}
        </p>
        <div class="profile-meta">
          <span>{{ profile.approved_seed_count }} 个投稿</span>
          <span>加入于 {{ new Date(profile.created_at).toLocaleDateString('zh-CN') }}</span>
        </div>
      </div>
    </div>

    <n-divider />

    <div class="tab-bar">
      <button
        :class="['tab-btn', { active: activeTab === 'seeds' }]"
        @click="switchTab('seeds')"
      >
        [ 投稿的种子 ]
      </button>
      <button
        v-if="isOwnProfile"
        :class="['tab-btn', { active: activeTab === 'likes' }]"
        @click="switchTab('likes')"
      >
        [ 赞过的种子 ]
      </button>
    </div>

    <div v-if="seedsLoading" class="loading">加载中...</div>
    <div v-else-if="seeds.length === 0" class="empty">暂无内容</div>
    <div v-else class="seed-grid">
      <SeedCard
        v-for="seed in seeds"
        :key="seed.id"
        :seed="seed"
        @updated="onSeedUpdated"
      />
    </div>
  </div>
</template>

<style scoped>
.container { max-width: 1280px; margin: 0 auto; padding: 32px 24px; }

.loading, .error, .empty {
  font-family: var(--font-micro); font-size: 0.75rem; color: var(--ink-dim);
  text-align: center; padding: 60px 0;
}

.profile-header {
  display: flex; align-items: center; gap: 20px;
}
.profile-avatar {
  width: 80px; height: 80px; border: 2px solid var(--border); flex-shrink: 0;
}
.profile-avatar-placeholder {
  width: 80px; height: 80px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: var(--ink-faint); border: 2px solid var(--border);
  font-family: var(--font-macro); font-size: 2rem; color: var(--ink-dim);
}

.profile-info { min-width: 0; }
.profile-name-row {
  display: flex; align-items: center; gap: 10px; margin-bottom: 4px;
}
.profile-name {
  font-family: var(--font-macro); font-size: 1.5rem; font-weight: 800;
}
.profile-mc {
  font-family: var(--font-micro); font-size: 0.75rem; color: var(--ink-dim);
  margin-bottom: 8px;
}
.profile-meta {
  display: flex; gap: 16px;
  font-family: var(--font-micro); font-size: 0.65rem; color: var(--ink-dim);
}

.tab-bar {
  display: flex; gap: 0; margin-bottom: 24px;
  border: 1px solid var(--border);
}
.tab-btn {
  padding: 8px 20px; cursor: pointer;
  font-family: var(--font-micro); font-size: 0.7rem; text-transform: uppercase;
  letter-spacing: 0.06em;
  border: none; border-right: 1px solid var(--border);
  background: var(--paper); color: var(--ink);
  transition: background 80ms, color 80ms;
}
.tab-btn:last-child { border-right: none; }
.tab-btn:hover { background: var(--ink-faint); }
.tab-btn.active { background: var(--ink); color: var(--paper); }

.seed-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
}
.seed-grid > * { background: var(--paper); }

@media (max-width: 768px) {
  .profile-header { flex-direction: column; text-align: center; }
  .seed-grid { grid-template-columns: 1fr; }
}
</style>
