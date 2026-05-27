<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NIcon } from 'naive-ui'
import { Flame, Add } from '@vicons/ionicons5'
import api from '@/api'
import type { SeedListItem } from '@/types'
import SeedCard from '@/components/SeedCard.vue'

const router = useRouter()
const hotSeeds = ref<SeedListItem[]>([])
const newSeeds = ref<SeedListItem[]>([])

onMounted(async () => {
  const [hotRes, newRes] = await Promise.all([
    api.get('/seeds', { params: { sort: 'popular', page_size: 8 } }),
    api.get('/seeds', { params: { sort: 'newest', page_size: 8 } }),
  ])
  hotSeeds.value = hotRes.data.data
  newSeeds.value = newRes.data.data
})

const quickTags = [
  { key: 'survival', icon: '🏕️', label: '生存' },
  { key: 'speedrun', icon: '⚔️', label: '速通' },
  { key: 'building', icon: '🏗️', label: '建筑' },
  { key: 'hardcore', icon: '💀', label: '极限' },
]
</script>

<template>
  <div class="home">
    <section class="brand-section">
      <h1 class="brand-title">S E E D &nbsp; V A U L T</h1>
      <p class="brand-sub">Minecraft 种子共享平台 · 发现、分享、复制你喜欢的 Minecraft 世界</p>
      <div class="quick-tags">
        <router-link
          v-for="qt in quickTags" :key="qt.key"
          :to="`/browse?tags=${qt.key}`"
          class="quick-tag"
        >
          <span class="qt-icon">{{ qt.icon }}</span>
          <span>{{ qt.label }}</span>
        </router-link>
      </div>
      <p class="brand-inspire">灵感来自斯瓦尔巴全球种子库 —— 保存、发现、再次开启</p>
    </section>

    <section class="seed-section">
      <div class="section-header">
        <h2><n-icon :component="Flame" /> 热门种子</h2>
        <router-link to="/browse?sort=popular">查看更多 →</router-link>
      </div>
      <div class="seed-grid">
        <SeedCard v-for="seed in hotSeeds" :key="seed.id" :seed="seed" />
      </div>
    </section>

    <section class="seed-section">
      <div class="section-header">
        <h2>最新投稿</h2>
        <router-link to="/browse?sort=newest">查看全部 →</router-link>
      </div>
      <div class="seed-grid">
        <SeedCard v-for="seed in newSeeds" :key="seed.id" :seed="seed" />
      </div>
    </section>

    <section class="cta-section">
      <p>没有找到想要的？</p>
      <router-link to="/submit">
        <n-button type="primary" size="large">
          <template #icon><n-icon :component="Add" /></template>
          提交你的种子
        </n-button>
      </router-link>
    </section>
  </div>
</template>

<style scoped>
.home { max-width: 1152px; margin: 0 auto; }
.brand-section {
  text-align: center; padding: 48px 24px 40px;
  border-bottom: 1px solid #e4e7eb; margin-bottom: 40px;
}
.brand-title {
  font-size: 28px; font-weight: 700; color: #1f2937;
  letter-spacing: 0.12em; margin-bottom: 12px;
}
.brand-sub { font-size: 16px; color: #6b7280; margin-bottom: 24px; }
.quick-tags { display: flex; justify-content: center; gap: 12px; margin-bottom: 20px; }
.quick-tag {
  display: flex; align-items: center; gap: 6px; padding: 8px 20px;
  background: #f0f2f5; border-radius: 8px; text-decoration: none;
  font-size: 15px; color: #4b5563; transition: background 150ms;
}
.quick-tag:hover { background: #e4e7eb; }
.qt-icon { font-size: 18px; }
.brand-inspire { font-size: 13px; color: #9ca3af; }
.seed-section { margin-bottom: 48px; }
.section-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;
}
.section-header h2 { font-size: 20px; font-weight: 600; color: #1f2937; display: flex; align-items: center; gap: 8px; }
.section-header a { font-size: 14px; color: #3b82f6; text-decoration: none; }
.seed-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(272px, 1fr));
  gap: 24px;
}
@media (max-width: 640px) {
  .seed-grid { grid-template-columns: 1fr; }
  .quick-tags { flex-wrap: wrap; }
}
.cta-section { text-align: center; padding: 40px 0; }
.cta-section p { margin-bottom: 16px; color: #6b7280; font-size: 15px; }
</style>
