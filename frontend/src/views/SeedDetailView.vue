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

const editionColor = computed(() =>
  seed.value?.edition === 'java' ? '#22c55e' : '#d97706'
)
const editionBg = computed(() =>
  seed.value?.edition === 'java' ? '#f0fdf4' : '#fffbeb'
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
              :style="{ color: editionColor, background: editionBg }"
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
              <n-tag v-if="seed.uploader.owns_java_edition" size="tiny" type="success">🎮 正版玩家</n-tag>
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
              <p style="margin-bottom:12px;font-size:13px;color:#6b7280">举报该种子</p>
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
.detail { display: flex; gap: 32px; }
.detail-main { flex: 1; min-width: 0; }
.screenshot-area { margin-bottom: 24px; border-radius: 8px; overflow: hidden; }
.carousel-img { width: 100%; aspect-ratio: 16/9; object-fit: cover; cursor: pointer; }
.no-screenshot { background: #f0f2f5; aspect-ratio: 16/9; display: flex; align-items: center; justify-content: center; color: #9ca3af; }
.seed-title { font-size: 24px; font-weight: 600; color: #1f2937; margin-bottom: 16px; }
.seed-desc { font-size: 15px; line-height: 1.7; color: #4b5563; }
.coords-section { margin-top: 24px; }
.coords-section h3 { font-size: 16px; font-weight: 600; margin-bottom: 12px; color: #374151; }
.coord-row { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid #f0f2f5; font-size: 14px; }
.coord-label { font-weight: 500; min-width: 100px; }
.coord-row code { font-family: "JetBrains Mono", monospace; font-size: 13px; color: #374151; }
.detail-sidebar { width: 340px; flex-shrink: 0; position: sticky; top: 80px; align-self: flex-start; }
.info-card { background: #fff; border: 1px solid #e4e7eb; border-radius: 8px; padding: 24px; }
.seed-value-block { text-align: center; }
.sv-label { font-size: 12px; color: #9ca3af; text-transform: uppercase; margin-bottom: 8px; }
.sv-value {
  font-family: "JetBrains Mono", monospace; font-size: 24px; font-weight: 500;
  color: #1f2937; letter-spacing: 0.02em; display: block; margin-bottom: 16px;
}
.info-rows { display: flex; flex-direction: column; gap: 10px; }
.info-row { display: flex; justify-content: space-between; align-items: center; font-size: 14px; }
.ir-label { color: #9ca3af; }
.edition-badge { font-size: 12px; font-weight: 500; padding: 1px 10px; border-radius: 999px; }
.tag-group { display: flex; flex-wrap: wrap; }
.uploader-info { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.uploader-avatar { width: 40px; height: 40px; border-radius: 4px; }
.uploader-name { font-size: 14px; font-weight: 500; }
.uploader-date { font-size: 12px; color: #9ca3af; }
.action-buttons { display: flex; flex-direction: column; gap: 8px; margin-top: 16px; }
@media (max-width: 768px) {
  .detail { flex-direction: column; }
  .detail-sidebar { width: 100%; position: static; }
}
</style>
