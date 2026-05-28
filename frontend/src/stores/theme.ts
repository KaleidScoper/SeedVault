import { defineStore } from 'pinia'
import { ref, computed, watchEffect } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'auto'

const STORAGE_KEY = 'seedvault_theme'

function getSystemPreference(): 'light' | 'dark' {
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyDOMTheme(resolved: 'light' | 'dark') {
  document.documentElement.setAttribute('data-theme', resolved)
}

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>(
    (localStorage.getItem(STORAGE_KEY) as ThemeMode) || 'auto'
  )

  const resolved = computed<'light' | 'dark'>(() => {
    if (mode.value === 'auto') return getSystemPreference()
    return mode.value
  })

  watchEffect(() => applyDOMTheme(resolved.value))

  const mql = window.matchMedia('(prefers-color-scheme: dark)')
  mql.addEventListener('change', () => {
    if (mode.value === 'auto') applyDOMTheme(getSystemPreference())
  })

  function setMode(next: ThemeMode) {
    mode.value = next
    localStorage.setItem(STORAGE_KEY, next)
    applyDOMTheme(resolved.value)
  }

  function cycle() {
    const order: ThemeMode[] = ['light', 'dark', 'auto']
    const idx = order.indexOf(mode.value)
    setMode(order[(idx + 1) % order.length])
  }

  const isDark = computed(() => resolved.value === 'dark')

  return { mode, resolved, isDark, setMode, cycle }
})
