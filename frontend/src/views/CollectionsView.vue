<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { NButton, NModal, NInput, NIcon, NSwitch, NEmpty, useMessage } from 'naive-ui'
import { Add, Trash, LockClosed, LockOpen } from '@vicons/ionicons5'
import api from '@/api'
import type { CollectionItem, SeedListItem } from '@/types'
import SeedCard from '@/components/SeedCard.vue'

const message = useMessage()
const collections = ref<CollectionItem[]>([])
const showCreate = ref(false)
const newName = ref('')
const newDesc = ref('')
const newPublic = ref(false)
const activeCollection = ref<{ id: number; name: string; seeds: SeedListItem[] } | null>(null)
const showDetail = ref(false)

onMounted(fetchCollections)

async function fetchCollections() {
  const { data } = await api.get('/collections')
  collections.value = data.data
}

async function createCollection() {
  if (!newName.value.trim()) return
  await api.post('/collections', { name: newName.value.trim(), description: newDesc.value || null, is_public: newPublic.value })
  message.success('收藏夹已创建')
  showCreate.value = false
  newName.value = ''
  newDesc.value = ''
  newPublic.value = false
  fetchCollections()
}

async function deleteCollection(id: number) {
  await api.delete(`/collections/${id}`)
  message.success('收藏夹已删除')
  fetchCollections()
}

async function viewCollection(c: CollectionItem) {
  const { data } = await api.get(`/collections/${c.id}`)
  activeCollection.value = {
    id: c.id,
    name: c.name,
    seeds: data.data.seeds || [],
  }
  showDetail.value = true
}
</script>

<template>
  <div class="collections-page">
    <div class="page-header">
      <h1>我的收藏夹</h1>
      <n-button type="primary" @click="showCreate = true">
        <template #icon><n-icon :component="Add" /></template>
        新建收藏夹
      </n-button>
    </div>

    <div v-if="collections.length === 0" class="empty">
      <n-empty description="还没有收藏夹" />
    </div>

    <div v-else class="collection-grid">
      <div
        v-for="c in collections" :key="c.id"
        class="collection-card"
        @click="viewCollection(c)"
      >
        <div class="cc-cover">
          <img v-if="c.cover_url" :src="c.cover_url" />
          <div v-else class="cc-cover-placeholder">
            <n-icon :component="c.is_public ? LockOpen : LockClosed" size="24" />
          </div>
        </div>
        <div class="cc-body">
          <h3>{{ c.name }}</h3>
          <p v-if="c.description" class="cc-desc">{{ c.description }}</p>
          <div class="cc-meta">
            <span>{{ c.seed_count }} 个种子</span>
            <span>{{ c.is_public ? '公开' : '私有' }}</span>
          </div>
        </div>
        <n-button text size="tiny" type="error" @click.stop="deleteCollection(c.id)">
          <template #icon><n-icon :component="Trash" /></template>
        </n-button>
      </div>
    </div>

    <!-- Create modal -->
    <n-modal v-model:show="showCreate" preset="card" title="新建收藏夹" style="width:400px">
      <div style="display:flex;flex-direction:column;gap:16px">
        <n-input v-model:value="newName" placeholder="收藏夹名称（必填）" maxlength="50" />
        <n-input v-model:value="newDesc" placeholder="描述（选填）" maxlength="200" type="textarea" rows="2" />
        <div style="display:flex;align-items:center;gap:8px">
          <n-switch v-model:value="newPublic" />
          <span style="font-size:14px">公开收藏夹</span>
        </div>
        <n-button type="primary" block @click="createCollection">创建</n-button>
      </div>
    </n-modal>

    <!-- Detail modal -->
    <n-modal v-model:show="showDetail" preset="card" :title="activeCollection?.name" style="max-width:800px">
      <div v-if="activeCollection" class="detail-seeds">
        <SeedCard v-for="seed in activeCollection.seeds" :key="seed.id" :seed="seed" />
      </div>
      <n-empty v-if="!activeCollection?.seeds.length" description="收藏夹为空" />
    </n-modal>
  </div>
</template>

<style scoped>
.collections-page { max-width: 900px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.page-header h1 { font-size: 24px; font-weight: 600; color: #1f2937; }
.collection-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
.collection-card {
  background: #fff; border: 1px solid #e4e7eb; border-radius: 8px;
  overflow: hidden; cursor: pointer; transition: box-shadow 150ms; position: relative;
}
.collection-card:hover { box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
.cc-cover { height: 120px; background: #f0f2f5; overflow: hidden; }
.cc-cover img { width: 100%; height: 100%; object-fit: cover; }
.cc-cover-placeholder { height: 100%; display: flex; align-items: center; justify-content: center; color: #9ca3af; }
.cc-body { padding: 12px 16px; }
.cc-body h3 { font-size: 15px; font-weight: 500; color: #1f2937; margin-bottom: 4px; }
.cc-desc { font-size: 13px; color: #9ca3af; margin-bottom: 8px; }
.cc-meta { font-size: 12px; color: #9ca3af; display: flex; gap: 12px; }
.detail-seeds { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
</style>
