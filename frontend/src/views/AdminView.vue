<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NTag, NModal, NInput, NIcon, NEmpty, useMessage } from 'naive-ui'
import { Checkmark, Close, ShieldCheckmark, Flag } from '@vicons/ionicons5'
import { useAuthStore } from '@/stores/auth'
import api from '@/api'

interface PendingSeed {
  id: number
  title: string
  seed_value: string
  edition: string
  tested_version: string
  uploader: { id: number; display_name: string } | null
  created_at: string
}

interface AdminReport {
  id: number
  seed_id: number
  seed_title: string
  reporter: { id: number; display_name: string } | null
  reason: string
  detail: string | null
  status: string
  created_at: string
}

const REASON_LABELS: Record<string, string> = {
  screenshot_mismatch: '截图不符',
  wrong_version: '版本错误',
  duplicate: '重复种子',
  inappropriate: '内容不当',
  other: '其他',
}

const router = useRouter()
const message = useMessage()
const auth = useAuthStore()

const adminTab = ref<'seeds' | 'reports'>('seeds')

const pendingSeeds = ref<PendingSeed[]>([])
const rejectReason = ref('')
const showReject = ref(false)
const rejectId = ref(0)

const reports = ref<AdminReport[]>([])
const reportsLoading = ref(false)

onMounted(async () => {
  if (!auth.isAdmin) { router.push('/'); return }
  await fetchPending()
})

async function fetchPending() {
  const { data } = await api.get('/admin/seeds/pending')
  pendingSeeds.value = data.data
}

async function fetchReports() {
  reportsLoading.value = true
  try {
    const { data } = await api.get('/admin/reports')
    reports.value = data.data
  } finally {
    reportsLoading.value = false
  }
}

function switchTab(tab: 'seeds' | 'reports') {
  adminTab.value = tab
  if (tab === 'reports') fetchReports()
}

async function approve(id: number) {
  await api.post(`/admin/seeds/${id}/approve`)
  message.success('已通过')
  pendingSeeds.value = pendingSeeds.value.filter(s => s.id !== id)
}

function openReject(id: number) {
  rejectId.value = id
  rejectReason.value = ''
  showReject.value = true
}

async function doReject() {
  await api.post(`/admin/seeds/${rejectId.value}/reject?reason=${encodeURIComponent(rejectReason.value)}`)
  message.success('已拒绝')
  showReject.value = false
  pendingSeeds.value = pendingSeeds.value.filter(s => s.id !== rejectId.value)
}

async function dismissReport(id: number) {
  await api.post(`/admin/reports/${id}/review?action=dismiss`)
  message.success('举报已驳回')
  reports.value = reports.value.filter(r => r.id !== id)
}

async function removeSeedByReport(report: AdminReport) {
  await api.post(`/admin/reports/${report.id}/review?action=remove_seed`)
  message.success('种子已移除')
  reports.value = reports.value.filter(r => r.id !== report.id)
}
</script>

<template>
  <div class="admin-page">
    <div class="page-header">
      <h1><n-icon :component="ShieldCheckmark" /> 审核后台</h1>
    </div>

    <div v-if="!auth.isAdmin" class="forbidden">
      <n-empty description="需要管理员权限" />
    </div>

    <div v-else>
      <div class="tab-bar">
        <button
          :class="['tab-btn', { active: adminTab === 'seeds' }]"
          @click="switchTab('seeds')"
        >
          [ 待审核种子 ]
        </button>
        <button
          :class="['tab-btn', { active: adminTab === 'reports' }]"
          @click="switchTab('reports')"
        >
          [ 举报管理 ]
        </button>
      </div>

      <!-- Seeds tab -->
      <div v-if="adminTab === 'seeds'">
        <div v-if="pendingSeeds.length === 0" class="empty">
          <n-empty description="没有待审核的种子" />
        </div>
        <div v-else class="pending-list">
          <div v-for="seed in pendingSeeds" :key="seed.id" class="pending-row">
            <div class="row-info">
              <h3>{{ seed.title }}</h3>
              <div class="row-meta">
                <span>种子值: {{ seed.seed_value }}</span>
                <n-tag size="tiny" :type="seed.edition === 'java' ? 'success' : 'warning'">
                  {{ seed.edition === 'java' ? 'Java' : '基岩' }} {{ seed.tested_version }}
                </n-tag>
                <span v-if="seed.uploader">投稿者: {{ seed.uploader.display_name }}</span>
                <span>{{ seed.created_at.slice(0, 10) }}</span>
              </div>
            </div>
            <div class="row-actions">
              <n-button type="success" size="small" @click="approve(seed.id)">
                <template #icon><n-icon :component="Checkmark" /></template> 通过
              </n-button>
              <n-button type="error" size="small" @click="openReject(seed.id)">
                <template #icon><n-icon :component="Close" /></template> 拒绝
              </n-button>
            </div>
          </div>
        </div>
      </div>

      <!-- Reports tab -->
      <div v-if="adminTab === 'reports'">
        <div v-if="reportsLoading" class="empty">加载中...</div>
        <div v-else-if="reports.length === 0" class="empty">
          <n-empty description="没有待处理的举报" />
        </div>
        <div v-else class="pending-list">
          <div v-for="r in reports" :key="r.id" class="pending-row">
            <div class="row-info">
              <h3>
                <router-link :to="`/seed/${r.seed_id}`" class="report-seed-link">
                  {{ r.seed_title }}
                </router-link>
              </h3>
              <div class="row-meta">
                <n-tag size="tiny" type="error">
                  {{ REASON_LABELS[r.reason] || r.reason }}
                </n-tag>
                <span v-if="r.reporter">举报者: {{ r.reporter.display_name }}</span>
                <span v-if="r.detail" class="report-detail">详情: {{ r.detail }}</span>
                <span>{{ r.created_at.slice(0, 10) }}</span>
              </div>
            </div>
            <div class="row-actions">
              <n-button size="small" @click="dismissReport(r.id)">
                <template #icon><n-icon :component="Close" /></template> 驳回
              </n-button>
              <n-button type="error" size="small" @click="removeSeedByReport(r)">
                <template #icon><n-icon :component="Checkmark" /></template> 移除种子
              </n-button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <n-modal v-model:show="showReject" preset="card" title="拒绝原因" style="width:400px">
      <div style="display:flex;flex-direction:column;gap:12px">
        <n-input v-model:value="rejectReason" placeholder="请填写拒绝原因" type="textarea" rows="3" />
        <n-button type="error" block @click="doReject">确认拒绝</n-button>
      </div>
    </n-modal>
  </div>
</template>

<style scoped>
.admin-page { max-width: 900px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-header h1 {
  font-family: var(--font-macro); font-size: 1.8rem; font-weight: 800;
  text-transform: uppercase; color: var(--ink);
  display: flex; align-items: center; gap: 8px;
}
.pending-list {
  display: flex; flex-direction: column;
  border: 1px solid var(--border);
}
.pending-row {
  background: var(--paper); padding: 16px 20px;
  display: flex; justify-content: space-between; align-items: center;
  border-bottom: 1px solid var(--border);
}
.pending-row:last-child { border-bottom: none; }
.pending-row:hover { background: var(--ink); }
.pending-row:hover .row-info h3,
.pending-row:hover .row-meta { color: var(--paper); }

.row-info h3 {
  font-family: var(--font-macro); font-size: 0.95rem; font-weight: 700;
  margin-bottom: 6px; color: var(--ink);
}
.row-meta {
  display: flex; gap: 16px;
  font-family: var(--font-micro); font-size: 0.65rem;
  color: var(--ink-dim); align-items: center;
}
.row-actions { display: flex; gap: 8px; }

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

.report-seed-link {
  color: var(--ink); text-decoration: none;
}
.report-seed-link:hover { text-decoration: underline; }
.pending-row:hover .report-seed-link { color: var(--paper); }
.report-detail {
  max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
</style>
