<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NIcon, NSelect, NEmpty, NPagination } from 'naive-ui'
import { Dice } from '@vicons/ionicons5'
import api from '@/api'
import { useMetaStore } from '@/stores/meta'
import type { SeedListItem, Version } from '@/types'
import SeedCard from '@/components/SeedCard.vue'

const route = useRoute()
const router = useRouter()
const meta = useMetaStore()

const seeds = ref<SeedListItem[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 24

const edition = ref<string | null>(null)
const version = ref<string | null>(null)
const worldType = ref<string | null>(null)
const tagFilter = ref<string | null>(null)
const modEnv = ref<string | null>(null)
const sort = ref('popular')
const searchQ = ref('')

onMounted(() => {
  edition.value = (route.query.edition as string) || null
  version.value = (route.query.version as string) || null
  worldType.value = (route.query.world_type as string) || null
  tagFilter.value = (route.query.tags as string) || null
  sort.value = (route.query.sort as string) || 'popular'
  searchQ.value = (route.query.q as string) || ''
  page.value = Number(route.query.page) || 1
  fetchSeeds()
})

async function fetchSeeds() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize, sort: sort.value }
    if (edition.value) params.edition = edition.value
    if (version.value) params.version = version.value
    if (worldType.value) params.world_type = worldType.value
    if (tagFilter.value) params.tags = tagFilter.value
    if (modEnv.value) params.mod_env = modEnv.value
    if (searchQ.value) params.q = searchQ.value
    const { data } = await api.get('/seeds', { params })
    seeds.value = data.data
    total.value = data.meta.total
  } finally {
    loading.value = false
  }
}

function updateRoute() {
  const query: any = {}
  if (edition.value) query.edition = edition.value
  if (version.value) query.version = version.value
  if (worldType.value) query.world_type = worldType.value
  if (tagFilter.value) query.tags = tagFilter.value
  if (modEnv.value) query.mod_env = modEnv.value
  if (sort.value !== 'popular') query.sort = sort.value
  if (searchQ.value) query.q = searchQ.value
  if (page.value > 1) query.page = page.value
  router.replace({ query })
  fetchSeeds()
}

watch([edition, version, worldType, tagFilter, modEnv, sort], () => { page.value = 1; updateRoute() })
watch(page, () => updateRoute())

const gameplayTags = computed(() => meta.tags.filter(t => t.category === 'gameplay'))
const featureTags = computed(() => meta.tags.filter(t => t.category === 'feature'))
const javaVersions = computed(() => meta.versions.filter(v => v.edition === 'java'))
const bedrockVersions = computed(() => meta.versions.filter(v => v.edition === 'bedrock'))

const sortOptions = [
  { label: '最热', value: 'popular' },
  { label: '最新', value: 'newest' },
  { label: '最多点赞', value: 'most_liked' },
  { label: '最多收藏', value: 'most_collected' },
]
const editionOptions = [
  { label: '全部', value: null },
  { label: 'Java 版', value: 'java' },
  { label: '基岩版', value: 'bedrock' },
] as any
const worldOptions = [
  { label: '全部', value: null },
  { label: '普通', value: 'normal' },
  { label: '大型群系', value: 'large_biomes' },
  { label: '超平坦', value: 'superflat' },
] as any
const modOptions = [
  { label: '全部', value: null },
  { label: '仅原版', value: 'vanilla' },
  { label: '含整合包', value: 'modpack' },
  { label: 'NeoForge', value: 'neoforge' },
] as any

function getVersionOptions() {
  if (!edition.value) return [{ label: '全部', value: null }]
  const vers = edition.value === 'java' ? javaVersions.value : bedrockVersions.value
  return [{ label: '全部', value: null }, ...vers.map(v => ({ label: v.version, value: v.version }))]
}

function randomSeed() {
  if (total.value === 0) return
  const randomPage = Math.floor(Math.random() * Math.min(total.value, 500)) + 1
  api.get('/seeds', { params: { page: randomPage, page_size: 1, sort: 'newest' } }).then(({ data }) => {
    if (data.data[0]) router.push(`/seed/${data.data[0].id}`)
  })
}
</script>

<template>
  <div class="browse">
    <aside class="filter-panel">
      <div class="filter-group">
        <label>版本端</label>
        <n-select v-model:value="edition" :options="editionOptions" clearable placeholder="全部" size="small" />
      </div>
      <div class="filter-group">
        <label>版本号</label>
        <n-select v-model:value="version" :options="getVersionOptions()" clearable placeholder="全部" size="small" />
      </div>
      <div class="filter-group">
        <label>世界类型</label>
        <n-select v-model:value="worldType" :options="worldOptions" clearable placeholder="全部" size="small" />
      </div>
      <div class="filter-group">
        <label>玩法标签</label>
        <div class="chip-group">
          <button
            v-for="t in gameplayTags" :key="t.key"
            :class="['chip', { active: tagFilter === t.key }]"
            @click="tagFilter = tagFilter === t.key ? null : t.key"
          >
            {{ t.icon }} {{ t.label }}
          </button>
        </div>
      </div>
      <div class="filter-group">
        <label>特性标签</label>
        <div class="chip-group">
          <button
            v-for="t in featureTags" :key="t.key"
            :class="['chip', { active: tagFilter === t.key }]"
            @click="tagFilter = tagFilter === t.key ? null : t.key"
          >
            {{ t.icon }} {{ t.label }}
          </button>
        </div>
      </div>
      <div class="filter-group">
        <label>Mod 环境</label>
        <n-select v-model:value="modEnv" :options="modOptions" clearable placeholder="全部" size="small" />
      </div>
      <n-button quaternary size="small" @click="edition=null;version=null;worldType=null;tagFilter=null;modEnv=null;sort='popular';searchQ='';page=1;updateRoute()">
        重置筛选
      </n-button>
    </aside>

    <div class="content">
      <div class="top-bar">
        <div class="sort-area">
          <n-select v-model:value="sort" :options="sortOptions" size="small" style="width:140px" />
          <n-button quaternary size="small" @click="randomSeed">
            <template #icon><n-icon :component="Dice" /></template>
            随机一个
          </n-button>
        </div>
        <span class="result-count">共 {{ total }} 个种子</span>
      </div>

      <div v-if="!loading && seeds.length > 0" class="seed-grid">
        <SeedCard v-for="seed in seeds" :key="seed.id" :seed="seed" @updated="fetchSeeds" />
      </div>
      <n-empty v-else-if="!loading" description="没有符合条件的结果，试试放宽筛选" />

      <div v-if="total > pageSize" class="pagination">
        <n-pagination
          v-model:page="page"
          :page-count="Math.ceil(total / pageSize)"
          :page-size="pageSize"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.browse { display: flex; gap: 32px; }
.filter-panel {
  width: 220px; flex-shrink: 0;
  position: sticky; top: 80px; align-self: flex-start;
}
.filter-group { margin-bottom: 20px; }
.filter-group label {
  display: block; font-size: 13px; font-weight: 500; color: #374151; margin-bottom: 6px;
}
.chip-group { display: flex; flex-wrap: wrap; gap: 6px; }
.chip {
  padding: 3px 10px; border: 1px solid #e4e7eb; border-radius: 4px;
  background: #fff; font-size: 12px; color: #6b7280; cursor: pointer;
  transition: all 150ms;
}
.chip:hover { border-color: #cbd0d6; }
.chip.active { background: #eff6ff; border-color: #3b82f6; color: #1d4ed8; }
.content { flex: 1; min-width: 0; }
.top-bar {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 20px;
}
.sort-area { display: flex; gap: 8px; align-items: center; }
.result-count { font-size: 13px; color: #9ca3af; }
.seed-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(256px, 1fr));
  gap: 20px;
}
.pagination { display: flex; justify-content: center; margin-top: 40px; }
@media (max-width: 768px) {
  .browse { flex-direction: column; }
  .filter-panel { width: 100%; position: static; }
  .filter-panel { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
}
</style>
