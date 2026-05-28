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

const editionStyle = computed(() =>
  props.seed.edition === 'java'
    ? { border: '1px solid var(--border)', background: 'var(--ink)', color: 'var(--paper)' }
    : { border: '1px solid var(--border)', background: 'var(--paper)', color: 'var(--ink)' }
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
            :style="editionStyle"
          >
            {{ seed.edition === 'java' ? 'Java' : '基岩' }} · {{ seed.tested_version }}
          </span>
          <span
            v-for="tag in seed.tags.slice(0, 2)"
            :key="tag.key"
            class="tag-chip"
          >
            {{ tag.category === 'gameplay' ? tag.icon + ' ' : '' }}{{ tag.label }}
          </span>
        </div>
        <div class="card-meta">
          <router-link
            v-if="seed.uploader"
            :to="`/user/${seed.uploader.id}`"
            class="meta-item uploader-link"
            @click.stop
          >
            {{ seed.uploader.minecraft_username || seed.uploader.display_name }}
          </router-link>
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
  background: var(--paper);
  border: 1px solid var(--border);
  overflow: hidden;
}
.seed-card:hover { background: var(--ink); }
.seed-card:hover .card-title { color: var(--paper); }
.seed-card:hover .card-desc { color: var(--paper); }
.seed-card:hover .meta-item { color: var(--paper); }

.card-link { text-decoration: none; color: inherit; display: block; }

.card-cover {
  position: relative; aspect-ratio: 16/9;
  background: var(--ink-faint);
  border-bottom: 1px solid var(--border);
  overflow: hidden;
}
.cover-img { width: 100%; height: 100%; object-fit: cover; }
.cover-placeholder {
  width: 100%; height: 100%; display: flex; align-items: center;
  justify-content: center; color: var(--ink-dim);
  font-family: var(--font-micro); font-size: 0.65rem;
  text-transform: uppercase; letter-spacing: 0.1em;
}

.copy-btn {
  position: absolute; top: 8px; right: 8px;
  background: var(--paper); border: 1px solid var(--border);
  padding: 3px 8px; cursor: pointer;
  display: flex; align-items: center; gap: 4px;
  font-family: var(--font-micro); font-size: 0.6rem;
  text-transform: uppercase;
}
.seed-card:not(:hover) .copy-btn { display: none; }

.card-body { padding: 12px 16px 16px; }

.card-title {
  font-family: var(--font-macro); font-size: 1rem; font-weight: 700;
  line-height: 1.25; color: var(--ink);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-bottom: 4px;
}

.card-desc {
  font-family: var(--font-micro); font-size: 0.68rem; color: var(--ink-dim);
  line-height: 1.4;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
  overflow: hidden; margin-bottom: 10px;
}

.card-tags {
  display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 10px;
}

.edition-badge {
  font-family: var(--font-micro); font-size: 0.6rem; font-weight: 500;
  text-transform: uppercase; letter-spacing: 0.06em;
  padding: 1px 8px;
}

.tag-chip {
  font-family: var(--font-micro); font-size: 0.6rem; color: var(--ink-dim);
  text-transform: uppercase; letter-spacing: 0.06em;
  padding: 1px 8px; border: 1px solid var(--border);
}

.card-meta { display: flex; gap: 12px; align-items: center; }

.meta-item {
  font-family: var(--font-micro); font-size: 0.65rem; color: var(--ink-dim);
  display: flex; align-items: center; gap: 3px;
}
.uploader-link {
  text-decoration: none; color: var(--ink-dim);
  transition: color 80ms;
}
.uploader-link:hover { color: var(--ink); text-decoration: underline; }
.seed-card:hover .uploader-link { color: var(--paper); }
</style>
