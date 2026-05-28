<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput, NSelect, NSteps, NStep, NUpload, NIcon, NTooltip, useMessage } from 'naive-ui'
import { ArrowBack, ArrowForward, Checkmark } from '@vicons/ionicons5'
import { useMetaStore } from '@/stores/meta'
import { useAuthStore } from '@/stores/auth'
import { GAMEPLAY_TAG_DESCRIPTIONS } from '@/constants/tags'
import api from '@/api'

const router = useRouter()
const message = useMessage()
const meta = useMetaStore()
const auth = useAuthStore()

const step = ref(1)
const submitting = ref(false)

// Step 1
const seedValue = ref('')
const edition = ref<'java' | 'bedrock'>('java')
const testedVersion = ref('')
const worldType = ref('normal')
const modEnv = ref('vanilla')
const modpackName = ref('')
const modpackVersion = ref('')

// Step 2
const spawnX = ref(0)
const spawnZ = ref(0)
const coords = ref<{ label: string; x: number; y: number | null; z: number }[]>([])
const screenshotIds = ref<number[]>([])
const uploading = ref(false)

// Step 3
const title = ref('')
const description = ref('')
const selectedTags = ref<string[]>([])

const editionOptions = [
  { label: 'Java 版', value: 'java' },
  { label: '基岩版', value: 'bedrock' },
]
const worldOptions = [
  { label: '普通', value: 'normal' },
  { label: '大型群系', value: 'large_biomes' },
  { label: '超平坦', value: 'superflat' },
]
const modOptions = [
  { label: '原版', value: 'vanilla' },
  { label: '整合包', value: 'modpack' },
  { label: 'NeoForge', value: 'neoforge' },
]

const versionOptions = computed(() => {
  const vers = edition.value === 'java'
    ? meta.versions.filter(v => v.edition === 'java')
    : meta.versions.filter(v => v.edition === 'bedrock')
  return vers.map(v => ({ label: v.version, value: v.version }))
})

const gameplayTags = computed(() => meta.tags.filter(t => t.category === 'gameplay'))
const featureTags = computed(() => meta.tags.filter(t => t.category === 'feature'))

async function handleUpload({ file }: any) {
  uploading.value = true
  try {
    const form = new FormData()
    form.append('file', file.file!)
    const { data } = await api.post('/upload/screenshot', form)
    screenshotIds.value.push(data.data.id)
    message.success('上传成功')
  } catch {
    message.error('上传失败')
  } finally {
    uploading.value = false
  }
  return false
}

function addCoord() {
  coords.value.push({ label: '', x: 0, y: null, z: 0 })
}

async function submit() {
  if (!auth.isLoggedIn) { message.warning('请先登录'); return }
  if (selectedTags.value.length === 0) { message.warning('请至少选择一个玩法标签'); return }
  submitting.value = true
  try {
    const { data } = await api.post('/seeds', {
      seed_value: seedValue.value,
      edition: edition.value,
      tested_version: testedVersion.value,
      world_type: worldType.value,
      mod_env: modEnv.value,
      modpack_name: modEnv.value === 'modpack' ? modpackName.value : null,
      modpack_version: modEnv.value === 'modpack' ? modpackVersion.value : null,
      spawn_x: spawnX.value,
      spawn_z: spawnZ.value,
      title: title.value,
      description: description.value,
      tags: selectedTags.value,
      key_coords: coords.value.filter(c => c.label.trim()),
      screenshot_ids: screenshotIds.value,
    })
    message.success('投稿已提交，等待审核')
    router.push(`/seed/${data.data.id}`)
  } catch (err: any) {
    message.error(err.response?.data?.detail?.message || '投稿失败')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="submit-page">
    <h1>提交种子</h1>

    <n-steps :current="step" style="margin-bottom:32px">
      <n-step title="基本信息" />
      <n-step title="截图与坐标" />
      <n-step title="标题与标签" />
    </n-steps>

    <!-- Step 1 -->
    <div v-if="step === 1" class="step-content">
      <div class="form-row">
        <label>种子值 <span class="required">*</span></label>
        <n-input v-model:value="seedValue" placeholder="如 123456789 或 Glacier" maxlength="64" />
      </div>
      <div class="form-row">
        <label>版本端 <span class="required">*</span></label>
        <n-select v-model:value="edition" :options="editionOptions" />
      </div>
      <div class="form-row">
        <label>测试版本 <span class="required">*</span></label>
        <n-select v-model:value="testedVersion" :options="versionOptions" />
      </div>
      <div class="form-row">
        <label>世界类型 <span class="required">*</span></label>
        <n-select v-model:value="worldType" :options="worldOptions" />
      </div>
      <div class="form-row">
        <label>Mod 环境 <span class="required">*</span></label>
        <n-select v-model:value="modEnv" :options="modOptions" />
      </div>
      <template v-if="modEnv === 'modpack'">
        <div class="form-row">
          <label>整合包名称 <span class="required">*</span></label>
          <n-input v-model:value="modpackName" placeholder="如 Terralith 2.5.4" />
        </div>
        <div class="form-row">
          <label>整合包版本</label>
          <n-input v-model:value="modpackVersion" placeholder="如 2.5.4" />
        </div>
      </template>
      <div class="step-actions">
        <n-button type="primary" @click="step = 2" :disabled="!seedValue || !testedVersion">
          下一步 <template #icon><n-icon :component="ArrowForward" /></template>
        </n-button>
      </div>
    </div>

    <!-- Step 2 -->
    <div v-if="step === 2" class="step-content">
      <div class="form-row">
        <label>截图 <span class="required">*</span>（1-5 张，第一张为封面）</label>
        <n-upload
          multiple
          :max="5"
          accept="image/jpeg,image/png,image/webp"
          :show-file-list="true"
          :custom-request="handleUpload"
        >
          <n-button :loading="uploading">选择图片</n-button>
        </n-upload>
        <p class="hint">已上传 {{ screenshotIds.length }} 张</p>
      </div>
      <div class="form-row">
        <label>出生点坐标 <span class="required">*</span></label>
        <div class="coord-inputs">
          <n-input v-model:value="spawnX" placeholder="X" style="width:120px" />
          <n-input v-model:value="spawnZ" placeholder="Z" style="width:120px" />
        </div>
      </div>
      <div class="form-row">
        <label>关键坐标</label>
        <div v-for="(c, i) in coords" :key="i" class="coord-inputs">
          <n-input v-model:value="c.label" placeholder="名称" style="width:140px" />
          <n-input v-model:value="c.x" placeholder="X" style="width:100px" />
          <n-input v-model:value="c.y" placeholder="Y（可选）" style="width:100px" />
          <n-input v-model:value="c.z" placeholder="Z" style="width:100px" />
        </div>
        <n-button text size="small" @click="addCoord">+ 添加坐标</n-button>
      </div>
      <div class="step-actions">
        <n-button @click="step = 1"><template #icon><n-icon :component="ArrowBack" /></template> 上一步</n-button>
        <n-button type="primary" @click="step = 3" :disabled="screenshotIds.length < 1">下一步 <template #icon><n-icon :component="ArrowForward" /></template></n-button>
      </div>
    </div>

    <!-- Step 3 -->
    <div v-if="step === 3" class="step-content">
      <div class="form-row">
        <label>标题 <span class="required">*</span>（≤50字）</label>
        <n-input v-model:value="title" maxlength="50" placeholder="为你的种子起个名字" />
      </div>
      <div class="form-row">
        <label>描述 <span class="required">*</span>（≤500字）</label>
        <n-input v-model:value="description" type="textarea" maxlength="500" placeholder="说明卖点、关键坐标等" rows="4" />
      </div>
      <div class="form-row">
        <label>玩法标签 <span class="required">*</span>（必选其一）</label>
        <div class="chip-group">
          <n-tooltip v-for="t in gameplayTags" :key="t.key" trigger="hover">
            <template #trigger>
              <button
                :class="['chip', { active: selectedTags.includes(t.key) }]"
                @click="selectedTags.includes(t.key) ? selectedTags = selectedTags.filter(k => k !== t.key) : selectedTags.push(t.key)"
              >
                {{ t.icon }} {{ t.label }}
              </button>
            </template>
            {{ GAMEPLAY_TAG_DESCRIPTIONS[t.key] }}
          </n-tooltip>
        </div>
      </div>
      <div class="form-row">
        <label>特性标签（可多选）</label>
        <div class="chip-group">
          <button
            v-for="t in featureTags" :key="t.key"
            :class="['chip', { active: selectedTags.includes(t.key) }]"
            @click="selectedTags.includes(t.key) ? selectedTags = selectedTags.filter(k => k !== t.key) : selectedTags.push(t.key)"
          >
            {{ t.icon }} {{ t.label }}
          </button>
        </div>
      </div>
      <div class="step-actions">
        <n-button @click="step = 2"><template #icon><n-icon :component="ArrowBack" /></template> 上一步</n-button>
        <n-button type="primary" :loading="submitting" @click="submit">
          <template #icon><n-icon :component="Checkmark" /></template> 提交投稿
        </n-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.submit-page { max-width: 720px; margin: 0 auto; }
h1 {
  font-family: var(--font-macro); font-size: 1.8rem; font-weight: 800;
  text-transform: uppercase; color: var(--ink); margin-bottom: 8px;
}
.step-content {
  background: var(--paper);
  border: 1px solid var(--border);
  padding: 32px;
}
.form-row { margin-bottom: 24px; }
.form-row label {
  display: block;
  font-family: var(--font-micro); font-size: 0.65rem;
  text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--ink); margin-bottom: 8px;
}
.required { color: var(--red); }
.hint {
  font-family: var(--font-micro); font-size: 0.65rem;
  color: var(--ink-faint); margin-top: 4px;
  letter-spacing: 0.04em;
}
.coord-inputs { display: flex; gap: 8px; margin-top: 8px; flex-wrap: wrap; }
.chip-group { display: flex; flex-wrap: wrap; gap: 4px; }
.chip {
  padding: 6px 14px;
  border: 1px solid var(--border);
  background: var(--paper);
  font-family: var(--font-micro); font-size: 0.7rem;
  text-transform: uppercase; letter-spacing: 0.04em;
  color: var(--ink); cursor: pointer;
  transition: background 80ms, color 80ms;
}
.chip:hover { background: var(--ink); color: var(--paper); }
.chip.active { background: var(--ink); color: var(--paper); }
.chip.active:hover { background: var(--red); border-color: var(--red); }
.step-actions {
  display: flex; justify-content: space-between;
  margin-top: 32px; padding-top: 24px;
  border-top: 2px solid var(--border);
}
</style>
