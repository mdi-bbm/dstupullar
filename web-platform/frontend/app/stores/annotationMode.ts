import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAnnotationModeStore = defineStore('annotationMode', () => {
  const mode = ref<'detection' | 'segmentation'>('detection')

  const initialize = () => {
    if (typeof window !== 'undefined' && localStorage) {
      const stored = localStorage.getItem('annotationMode')
      if (stored === 'detection' || stored === 'segmentation') {
        mode.value = stored
      }
    }
  }
  
  const setMode = (newMode: 'detection' | 'segmentation') => {
    mode.value = newMode
    if (typeof window !== 'undefined' && localStorage) {
      localStorage.setItem('annotationMode', newMode)
    }
  }
  
  return {
    mode,
    initialize,
    setMode
  }
})