<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import {
  NButton, NIcon, NCarousel, NTag, NDivider, NModal, NImage,
  NPopover, useMessage,
} from 'naive-ui'
import { Copy, Heart, Flag, FolderOpen, CheckmarkCircle } from '@vicons/ionicons5'
import api from '@/api'
import { useAuthStore } from '@/stores/auth'
import type { SeedDetail } from '@/types'

const route = useRoute()
const message = useMessage()
const auth = useAuthStore()
const seed = ref<SeedDetail | null>(null)
const loading = ref(true)
const showLightbox = ref(false)
const lightboxIndex = ref(0)

onMounted(async () => {
  try {
    const { data } = await api.get(`/seeds/${route.params.id}`)
    seed.value = data.data
  } finally {
    loading.value = false
  }
})

const editionStyle = computed(() =>
  seed.value?.edition === 'java'
    ? { border: '1px solid var(--border)', background: 'var(--ink)', color: 'var(--paper)' }
    : { border: '1px solid var(--border)', background: 'var(--paper)', color: 'var(--ink)' }
)

async function copySeed() {
  if (!seed.value) return
  try {
    await navigator.clipboard.writeText(seed.value.seed_value)
    message.success('种子值已复制到剪贴板')
  } catch {
    message.warning('请手动复制')
  }
}

function copyCoord(label: string, x: number, y: number | null, z: number) {
  const text = y != null ? `${label} X:${x} Y:${y} Z:${z}` : `${label} X:${x} Z:${z}`
  navigator.clipboard.writeText(text).then(() => message.success('坐标已复制'))
}

async function toggleLike() {
  if (!auth.isLoggedIn) { message.warning('请先登录'); return }
  if (!seed.value) return
  try {
    const { data } = await api.post(`/seeds/${seed.value.id}/like`)
    seed.value.is_liked = data.data.liked
    seed.value.like_count = data.data.like_count
  } catch { message.error('操作失败') }
}
</script>

<template>
  <div v-if="loading" class="loading">加载中...</div>
  <div v-else-if="!seed" class="error">种子不存在或已被删除</div>
  <div v-else class="detail">
    <div class="detail-main">
      <div class="screenshot-area">
        <n-carousel v-if="seed.screenshots.length > 0" draggable>
          <img
            v-for="ss in seed.screenshots" :key="ss.id"
            :src="ss.url"
            class="carousel-img"
            @click="lightboxIndex = seed.screenshots.findIndex(s => s.id === ss.id); showLightbox = true"
          />
        </n-carousel>
        <div v-else class="no-screenshot">暂无截图</div>
      </div>

      <h1 class="seed-title">{{ seed.title }}</h1>
      <div class="seed-desc" v-html="seed.description.replace(/\n/g, '<br>')"></div>

      <n-divider />

      <div v-if="seed.key_coords.length > 0" class="coords-section">
        <h3>关键坐标</h3>
        <div v-for="kc in seed.key_coords" :key="kc.id" class="coord-row">
          <span class="coord-label">{{ kc.label }}</span>
          <code>X: {{ kc.x }}</code>
          <code v-if="kc.y != null">Y: {{ kc.y }}</code>
          <code>Z: {{ kc.z }}</code>
          <n-button text size="tiny" @click="copyCoord(kc.label, kc.x, kc.y, kc.z)">
            <template #icon><n-icon :component="Copy" /></template>
          </n-button>
        </div>
      </div>
    </div>

    <aside class="detail-sidebar">
      <div class="info-card">
        <div class="seed-value-block">
          <div class="sv-label">种子值</div>
          <code class="sv-value">{{ seed.seed_value }}</code>
          <n-button type="primary" block size="large" @click="copySeed">
            <template #icon><n-icon :component="Copy" /></template>
            复制种子值
          </n-button>
        </div>

        <n-divider />

        <div class="info-rows">
          <div class="info-row">
            <span class="ir-label">版本端</span>
            <span
              class="edition-badge"
              :style="editionStyle"
            >
              {{ seed.edition === 'java' ? 'Java' : '基岩' }} · {{ seed.tested_version }}
            </span>
          </div>
          <div v-if="seed.compatible_range" class="info-row">
            <span class="ir-label">兼容范围</span>
            <span>{{ seed.compatible_range }}</span>
          </div>
          <div class="info-row">
            <span class="ir-label">世界类型</span>
            <span>{{ { normal: '普通', large_biomes: '大型群系', superflat: '超平坦' }[seed.world_type] }}</span>
          </div>
          <div class="info-row">
            <span class="ir-label">Mod 环境</span>
            <span>
              {{ { vanilla: '原版', modpack: '整合包', neoforge: 'NeoForge' }[seed.mod_env] }}
              <template v-if="seed.modpack_name"> ({{ seed.modpack_name }})</template>
            </span>
          </div>
          <div class="info-row">
            <span class="ir-label">出生点</span>
            <code>X: {{ seed.spawn_x }} Z: {{ seed.spawn_z }}</code>
          </div>
        </div>

        <n-divider />

        <div class="tag-group">
          <n-tag v-for="t in seed.tags" :key="t.key" size="small" style="margin:0 6px 6px 0">
            {{ t.icon }} {{ t.label }}
          </n-tag>
        </div>

        <n-divider />

        <div v-if="seed.uploader" class="uploader-info">
          <img
            v-if="seed.uploader.avatar_url"
            :src="seed.uploader.avatar_url"
            class="uploader-avatar"
          />
          <div>
            <div class="uploader-name">
              {{ seed.uploader.minecraft_username || seed.uploader.display_name }}
              <n-tag v-if="seed.uploader.owns_java_edition" size="tiny" type="success">&#x25C9; 正版玩家</n-tag>
            </div>
            <div class="uploader-date">{{ seed.created_at.slice(0, 10) }}</div>
          </div>
        </div>

        <div class="action-buttons">
          <n-button block size="large" :type="seed.is_liked ? 'primary' : 'default'" @click="toggleLike">
            <template #icon><n-icon :component="Heart" /></template>
            点赞 ({{ seed.like_count }})
          </n-button>
          <n-popover trigger="click">
            <template #trigger>
              <n-button block size="small" quaternary>
                <template #icon><n-icon :component="Flag" /></template>
                举报
              </n-button>
            </template>
            <div style="padding:12px;width:240px">
              <p style="margin-bottom:12px;font-size:13px;color:var(--ink-dim)">举报该种子</p>
              <n-button size="small" type="error" @click="message.success('举报已提交')">确认举报</n-button>
            </div>
          </n-popover>
        </div>
      </div>
    </aside>

    <n-modal v-model:show="showLightbox" preset="card" style="max-width:90vw" title="">
      <img
        v-if="seed.screenshots[lightboxIndex]"
        :src="seed.screenshots[lightboxIndex].url"
        style="width:100%"
      />
    </n-modal>
  </div>
</template>

<style scoped>
.detail {
  display: grid; grid-template-columns: 1fr 360px;
  gap: 1px; background: var(--border);
  border: 1px solid var(--border);
}
.detail-main {
  background: var(--paper); padding: 24px; min-width: 0;
}
.screenshot-area {
  margin-bottom: 24px; border: 1px solid var(--border); overflow: hidden;
}
.carousel-img { width: 100%; aspect-ratio: 16/9; object-fit: cover; cursor: pointer; display: block; }
.no-screenshot {
  background: var(--ink-faint); aspect-ratio: 16/9;
  display: flex; align-items: center; justify-content: center;
  font-family: var(--font-micro); font-size: 0.65rem;
  text-transform: uppercase; letter-spacing: 0.1em; color: var(--ink-dim);
}
.seed-title {
  font-family: var(--font-macro); font-size: 1.6rem; font-weight: 800;
  color: var(--ink); margin-bottom: 16px;
}
.seed-desc {
  font-family: var(--font-micro); font-size: 0.8rem; line-height: 1.7;
  color: var(--ink);
}
.coords-section { margin-top: 24px; }
.coords-section h3 {
  font-family: var(--font-micro); font-size: 0.65rem; font-weight: 500;
  text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--ink-dim); margin-bottom: 12px;
}
.coord-row {
  display: flex; align-items: center; gap: 10px; padding: 8px 0;
  border-bottom: 1px solid var(--ink-faint);
  font-family: var(--font-micro); font-size: 0.75rem;
}
.coord-label { font-weight: 500; min-width: 100px; }
.coord-row code {
  font-family: var(--font-micro); font-size: 0.75rem; color: var(--ink);
}

.detail-sidebar {
  background: var(--paper); padding: 24px;
  position: sticky; top: 80px; align-self: flex-start;
  max-height: calc(100vh - 100px); overflow-y: auto;
}
.info-card { padding: 0; }

.seed-value-block {
  text-align: center; padding: 20px;
  border: 1px solid var(--border); margin-bottom: 24px;
}
.sv-label {
  font-family: var(--font-micro); font-size: 0.6rem;
  text-transform: uppercase; letter-spacing: 0.12em;
  color: var(--ink-dim); margin-bottom: 8px;
}
.sv-value {
  font-family: var(--font-micro); font-size: 1.4rem; font-weight: 700;
  letter-spacing: 0.04em; color: var(--ink);
  display: block; margin-bottom: 16px; word-break: break-all;
}

.info-rows { display: flex; flex-direction: column; }
.info-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 0; border-bottom: 1px solid var(--ink-faint);
  font-family: var(--font-micro); font-size: 0.75rem;
}
.info-row:last-child { border-bottom: none; }
.ir-label {
  font-family: var(--font-micro); font-size: 0.65rem;
  text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--ink-dim);
}
.edition-badge {
  font-family: var(--font-micro); font-size: 0.65rem; font-weight: 500;
  text-transform: uppercase; letter-spacing: 0.06em;
  padding: 1px 10px;
}
.tag-group { display: flex; flex-wrap: wrap; margin: 16px 0; }
.uploader-info {
  display: flex; align-items: center; gap: 12px; margin-bottom: 16px;
  padding-top: 12px; border-top: 1px solid var(--border);
}
.uploader-avatar { width: 36px; height: 36px; }
.uploader-name {
  font-family: var(--font-micro); font-size: 0.75rem; font-weight: 500;
}
.uploader-date {
  font-family: var(--font-micro); font-size: 0.65rem;
  color: var(--ink-dim);
}
.action-buttons {
  display: flex; flex-direction: column; gap: 8px;
  margin-top: 20px; padding-top: 20px;
  border-top: 2px solid var(--border);
}

@media (max-width: 768px) {
  .detail { grid-template-columns: 1fr; }
  .detail-sidebar { position: static; max-height: none; }
}
</style>
