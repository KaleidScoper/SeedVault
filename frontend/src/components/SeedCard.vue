<script setup lang="ts">
import { computed } from 'vue'
import { NTag, NButton, NIcon, useMessage } from 'naive-ui'
import { Heart, Eye, Folder, Copy } from '@vicons/ionicons5'
import type { SeedListItem } from '@/types'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

const props = defineProps<{ seed: SeedListItem }>()
const emit = defineEmits<{ updated: [] }>()
const message = useMessage()
const auth = useAuthStore()

const editionColor = computed(() =>
  props.seed.edition === 'java' ? '#22c55e' : '#d97706'
)
const editionBg = computed(() =>
  props.seed.edition === 'java' ? '#f0fdf4' : '#fffbeb'
)

async function copySeed(e: MouseEvent) {
  e.stopPropagation()
  try {
    await navigator.clipboard.writeText(props.seed.seed_value)
    message.success('种子值已复制')
  } catch {
    message.warning('请手动复制')
  }
}

async function toggleLike(e: MouseEvent) {
  e.stopPropagation()
  if (!auth.isLoggedIn) {
    message.warning('请先登录')
    return
  }
  try {
    await api.post(`/seeds/${props.seed.id}/like`)
    emit('updated')
  } catch {
    message.error('操作失败')
  }
}

function formatCount(n: number): string {
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}
</script>

<template>
  <div class="seed-card">
    <router-link :to="`/seed/${seed.id}`" class="card-link">
      <div class="card-cover">
        <img
          v-if="seed.cover_url"
          :src="seed.cover_url"
          :alt="seed.title"
          loading="lazy"
          class="cover-img"
        />
        <div v-else class="cover-placeholder">No Image</div>
        <button class="copy-btn" @click="copySeed" title="复制种子值">
          <n-icon size="16" :component="Copy" />
        </button>
      </div>
      <div class="card-body">
        <h3 class="card-title">{{ seed.title }}</h3>
        <p class="card-desc">{{ seed.description_preview }}</p>
        <div class="card-tags">
          <span
            class="edition-badge"
            :style="{ color: editionColor, background: editionBg }"
          >
            {{ seed.edition === 'java' ? 'Java' : '基岩' }} · {{ seed.tested_version }}
          </span>
          <span
            v-for="tag in seed.tags.slice(0, 2)"
            :key="tag.key"
            class="tag-chip"
          >
            {{ tag.icon }} {{ tag.label }}
          </span>
        </div>
        <div class="card-meta">
          <span v-if="seed.uploader" class="meta-item">
            {{ seed.uploader.minecraft_username || seed.uploader.display_name }}
          </span>
          <span class="meta-item">
            <n-icon size="14" :component="Heart" />
            {{ formatCount(seed.like_count) }}
          </span>
          <span class="meta-item">
            <n-icon size="14" :component="Folder" />
            {{ seed.collection_count }}
          </span>
          <span class="meta-item">
            <n-icon size="14" :component="Eye" />
            {{ formatCount(seed.view_count) }}
          </span>
        </div>
      </div>
    </router-link>
  </div>
</template>

<style scoped>
.seed-card {
  background: #fff; border: 1px solid #e4e7eb; border-radius: 8px;
  overflow: hidden; transition: box-shadow 150ms;
}
.seed-card:hover { box-shadow: 0 1px 3px rgba(0,0,0,0.06); border-color: #cbd0d6; }
.card-link { text-decoration: none; color: inherit; display: block; }
.card-cover {
  position: relative; aspect-ratio: 16/9; background: #f0f2f5; overflow: hidden;
}
.cover-img { width: 100%; height: 100%; object-fit: cover; }
.cover-placeholder {
  width: 100%; height: 100%; display: flex; align-items: center;
  justify-content: center; color: #9ca3af; font-size: 14px;
}
.copy-btn {
  position: absolute; top: 8px; right: 8px; opacity: 0;
  background: rgba(255,255,255,0.9); border: 1px solid #e4e7eb;
  border-radius: 6px; padding: 4px 8px; cursor: pointer;
  transition: opacity 150ms; display: flex; align-items: center; gap: 4px;
}
.seed-card:hover .copy-btn { opacity: 1; }
.card-body { padding: 12px 16px 16px; }
.card-title {
  font-size: 16px; font-weight: 500; color: #1f2937;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 4px;
}
.card-desc {
  font-size: 13px; color: #9ca3af; line-height: 1.4;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; margin-bottom: 10px;
}
.card-tags {
  display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px;
}
.edition-badge {
  font-size: 11px; font-weight: 500; padding: 1px 8px; border-radius: 999px;
}
.tag-chip {
  font-size: 11px; color: #6b7280; background: #f0f2f5;
  padding: 1px 8px; border-radius: 4px;
}
.card-meta { display: flex; gap: 12px; align-items: center; }
.meta-item {
  font-size: 12px; color: #9ca3af; display: flex; align-items: center; gap: 3px;
}
</style>
