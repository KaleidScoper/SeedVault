<script setup lang="ts">
import { NButton, NIcon, NTooltip } from 'naive-ui'
import { SunnyOutline, MoonOutline } from '@vicons/ionicons5'
import { useThemeStore } from '@/stores/theme'

const theme = useThemeStore()

const tooltipMap: Record<string, string> = {
  light: '浅色模式',
  dark: '暗色模式',
  auto: '跟随系统',
}
</script>

<template>
  <n-tooltip>
    <template #trigger>
      <n-button quaternary circle size="medium" @click="theme.cycle()">
        <template #icon>
          <n-icon :component="theme.isDark ? MoonOutline : SunnyOutline" />
        </template>
      </n-button>
    </template>
    {{ tooltipMap[theme.mode] }}
  </n-tooltip>
</template>
