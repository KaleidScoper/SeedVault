import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api'
import type { AuthUser } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<AuthUser | null>(null)
  const loading = ref(false)

  const isLoggedIn = computed(() => !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function fetchMe() {
    try {
      loading.value = true
      const { data } = await api.get('/auth/me')
      user.value = data.data
    } catch {
      user.value = null
    } finally {
      loading.value = false
    }
  }

  async function devLogin(userId: number) {
    await api.post(`/auth/dev-login?user_id=${userId}`)
    await fetchMe()
  }

  async function logout() {
    await api.post('/auth/logout')
    user.value = null
  }

  return { user, loading, isLoggedIn, isAdmin, fetchMe, devLogin, logout }
})
