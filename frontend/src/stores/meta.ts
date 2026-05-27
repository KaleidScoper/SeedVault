import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { Tag, Version } from '@/types'
import api from '@/api'

export const useMetaStore = defineStore('meta', () => {
  const tags = ref<Tag[]>([])
  const versions = ref<Version[]>([])

  async function fetchTags() {
    const { data } = await api.get('/tags')
    tags.value = data.data
  }

  async function fetchVersions() {
    const { data } = await api.get('/versions')
    versions.value = data.data
  }

  function getTag(key: string): Tag | undefined {
    return tags.value.find(t => t.key === key)
  }

  return { tags, versions, fetchTags, fetchVersions, getTag }
})
