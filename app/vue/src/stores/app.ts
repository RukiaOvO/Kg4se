import { defineStore } from 'pinia'
import { ref } from 'vue'
import i18n from '@/i18n'

export const useAppStore = defineStore('app', () => {
  const language = ref<'zh' | 'en'>(localStorage.getItem('language') as 'zh' | 'en' || 'zh')
  const loading = ref<boolean>(false)

  const setLanguage = (lang: 'zh' | 'en') => {
    language.value = lang
    // The type of i18n.global.locale may be either a Ref or a string depending on vue-i18n version.
    // Cast to any for assignment to keep TypeScript happy.
    ;(i18n.global as any).locale = lang
    localStorage.setItem('language', lang)
  }

  return {
    language,
    loading,
    setLanguage
  }
})

