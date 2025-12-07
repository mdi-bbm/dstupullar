import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'
import 'vuetify/styles'

export default defineNuxtPlugin((nuxtApp) => {
  const vuetify = createVuetify({
    components,
    directives,
    theme: {
      defaultTheme: 'dark',
      themes: {
        dark: {
          colors: {
            primary: '#BB86FC',
            secondary: '#03DAC6',
            accent: '#FF4081',
            background: '#121212'
          }
        }
      }
    }
  })
  nuxtApp.vueApp.use(vuetify)
  
})
