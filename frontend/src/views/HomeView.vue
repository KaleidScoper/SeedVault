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
  { key: 'survival', icon: '■', label: '生存向' },
  { key: 'speedrun', icon: '▲', label: '速通向' },
  { key: 'building', icon: '◆', label: '建筑向' },
  { key: 'hardcore', icon: '✛', label: '极限模式' },
]
</script>

<template>
  <div class="home">
    <section class="brand-section">
      <h1 class="brand-title">
        <span class="brand-line">SEED</span>
        <span class="brand-line brand-line--red">VAULT</span>
      </h1>
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
.home { max-width: 1280px; margin: 0 auto; }

.brand-section {
  text-align: center;
  padding: clamp(80px, 12vh, 120px) 24px clamp(64px, 10vh, 96px);
  border-bottom: 2px solid var(--border); margin-bottom: 48px;
  min-height: calc(100vh - 56px - 64px);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}

.brand-title {
  display: flex; flex-direction: column; gap: 0;
  margin-bottom: 24px;
}

.brand-line {
  font-family: var(--font-macro);
  font-size: clamp(3.5rem, 9vw, 12rem);
  font-weight: 900; text-transform: uppercase;
  letter-spacing: -0.05em; line-height: 0.82;
  color: var(--ink);
  display: block;
}

.brand-line--red { color: var(--red); }

.brand-sub {
  font-family: var(--font-micro); font-size: 0.75rem;
  color: var(--ink-dim); letter-spacing: 0.06em;
  margin-bottom: 32px; max-width: 520px; margin-left: auto; margin-right: auto;
  line-height: 1.6;
}

.quick-tags {
  display: inline-flex; gap: 0; margin-bottom: 24px;
  border: 1px solid var(--border);
}

.quick-tag {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 24px; text-decoration: none;
  font-family: var(--font-micro); font-size: 0.7rem;
  text-transform: uppercase; letter-spacing: 0.06em;
  color: var(--ink);
  border-right: 1px solid var(--border);
  transition: background 80ms, color 80ms;
}
.quick-tag:last-child { border-right: none; }
.quick-tag:hover { background: var(--ink); color: var(--paper); }

.qt-icon { font-size: 0.85rem; }

.brand-inspire {
  font-family: var(--font-micro); font-size: 0.6rem;
  text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--ink-faint);
}

.seed-section { margin-bottom: 56px; }

.section-header {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 20px; padding-bottom: 10px;
  border-bottom: 1px solid var(--border);
}
.section-header h2 {
  font-family: var(--font-micro); font-size: 0.7rem; font-weight: 500;
  text-transform: uppercase; letter-spacing: 0.1em;
  color: var(--ink); display: flex; align-items: center; gap: 8px;
}
.section-header a {
  font-family: var(--font-micro); font-size: 0.65rem;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--ink-dim); text-decoration: none;
}
.section-header a:hover { color: var(--ink); }

.seed-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(272px, 1fr));
  gap: 1px;
  background: var(--border);
  border: 1px solid var(--border);
}

@media (max-width: 640px) {
  .seed-grid { grid-template-columns: 1fr; }
  .quick-tags { flex-wrap: wrap; }
}

.cta-section { text-align: center; padding: 48px 0; }
.cta-section p {
  font-family: var(--font-micro); font-size: 0.75rem;
  color: var(--ink-dim); margin-bottom: 20px;
}
</style>
