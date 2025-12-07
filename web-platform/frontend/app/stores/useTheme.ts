import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<'dark' | 'light'>('dark')

  const initialize = () => {
    if (typeof window !== 'undefined' && localStorage) {
      const stored = localStorage.getItem('theme')
      if (stored === 'dark' || stored === 'light') {
        theme.value = stored
      }
    }
  }
  
  const setTheme = (newTheme: 'dark' | 'light') => {
    theme.value = newTheme
    if (typeof window !== 'undefined' && localStorage) {
      localStorage.setItem('theme', newTheme)
    }
  }
  
  return {
    theme,
    initialize,
    setTheme
  }
})