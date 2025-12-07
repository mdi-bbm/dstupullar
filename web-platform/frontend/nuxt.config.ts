import { defineNuxtConfig } from 'nuxt/config'
import tsconfigPaths from 'vite-tsconfig-paths'

export default defineNuxtConfig({
  devtools: { enabled: true },
  typescript: {
    typeCheck: true
  }, 
  css: [
    'vuetify/styles',
    '@/assets/css/style.css', 
    '@mdi/font/css/materialdesignicons.min.css'
  ],

  modules: [
    '@pinia/nuxt',
    '@nuxtjs/i18n', 
    
    
  ],


  build: {
    transpile: ['vuetify']
  },

  app: {
    head: {
      title: 'PULLAR',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' }
      ],
      link: [{ rel: 'icon', href: '/favicon.ico' }]
    }
  },

  
   nitro: {
    routeRules: {
      '/api/**': {
        proxy: {
          to: `${process.env.BASE_FRONT_URL}/api/**`,
          
        }
      }
    }
  },
  runtimeConfig: {
    public: {
      apiBase: process.env.BASE_FRONT_URL,
      
    }
  },

  devServer: {
    host: '0.0.0.0',
    port: 6448
  },

  i18n: {
    defaultLocale: 'en',
    strategy: 'no_prefix',
    locales: [
      { code: 'en', name: 'English', file: 'en.js' },
      { code: 'ru', name: 'Russian', file: 'ru.js' }
    ]
  },
  vite: {
    plugins: [tsconfigPaths()]
  }
})
