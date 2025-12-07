import type { NuxtI18nOptions } from '@nuxtjs/i18n'

const i18nConfig: NuxtI18nOptions = {
  defaultLocale: 'ru',
  langDir: 'i18n/locales',
  locales: [
    { code: 'en', file: 'en.json', name: 'English' },
    { code: 'ru', file: 'ru.json', name: 'Русский' }
  ], 
  strategy: 'no_prefix',
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'i18n_redirected',
      redirectOn: 'root'
    }
}

export default i18nConfig
