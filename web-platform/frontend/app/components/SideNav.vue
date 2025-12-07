<template>
  <v-navigation-drawer
    app
    permanent
    v-model="drawer"
    :rail="rail"
    mini-variant-width="72"
    width="280"
    expand-on-hover
    class="custom-drawer transition-all side-nav"
    :class="{ 'dark-theme-drawer': isDark, 'light-theme-drawer': !isDark }"
    >

    <v-list density="compact">

      <v-list-item v-show="loggedIn" class="user-item">
        <template v-slot:prepend>
          <v-avatar size="40" class="user-avatar">
            <v-img :src="defaultAvatar" alt="User Avatar" contain />
          </v-avatar>
        </template>
        
        <template v-slot:title>
          <span class="font-weight-bold text-h6 text-uppercase fade-in-text user-name">
            {{ user?.username }}
          </span>
        </template>
      </v-list-item>

      <v-divider class="my-2 divider" />

      <template v-if="loggedIn">
        <v-list-item
          v-for="item in authLinks"
          :key="item.to"
          :to="item.to"
          link
          class="nav-item animated-btn"
          :active-class="'v-item--active'"
          >
          <template v-slot:prepend>
            <v-icon>{{ item.icon }}</v-icon>
          </template>
          
          <template v-slot:title>
            <span class="text-h6 fade-in-text">{{ $t(item.titleKey) }}</span>
          </template>
        </v-list-item>

        <v-list-item
          @click="logout"
          link
          class="nav-item animated-btn logout-btn"
          >
          <template v-slot:prepend>
            <v-icon color="error">mdi-logout</v-icon>
          </template>
          
          <template v-slot:title>
            <span class="text-h6 fade-in-text text-error">{{ $t('navigator.signout') }}</span>
          </template>
        </v-list-item>
      </template>

      <template v-else>
        <v-list-item
          v-for="item in guestLinks"
          :key="item.to"
          :to="item.to"
          link
          class="nav-item animated-btn"
          :active-class="'v-item--active'"
          >
          <template v-slot:prepend>
            <v-icon>{{ item.icon }}</v-icon>
          </template>
          
          <template v-slot:title>
            <span class="text-h6 fade-in-text">{{ $t(item.titleKey) }}</span>
          </template>
        </v-list-item>
      </template>

      <v-divider class="my-2 divider" />

      <div class="flex-grow-1"></div>

      <v-list-item class="switch-item">
        <template v-slot:prepend>
          <v-icon :color="isDark ? 'blue' : 'orange'" class="switch-icon">
            {{ isDark ? 'mdi-weather-night' : 'mdi-weather-sunny' }}
          </v-icon>
        </template>
        
        <template v-slot:title>
          <v-switch
            v-model="isDark"
            inset
            hide-details
            @update:model-value="toggleTheme"
            class="theme-toggle"
            density="compact"
          />
        </template>
      </v-list-item>

      <v-list-item class="switch-item">
        <template v-slot:prepend>
          <div class="text-lg font-bold lang-label">{{ currentLang.toUpperCase() }}</div>
        </template>
        
        <template v-slot:title>
          <v-switch
            v-model="langSwitch"
            inset
            hide-details
            @update:model-value="toggleLang"
            class="theme-toggle"
            density="compact"
          />
        </template>
      </v-list-item>

    </v-list>
  </v-navigation-drawer>
</template>

<script setup>
import { useTheme } from 'vuetify'
import { ref, computed, watch, onMounted } from 'vue'
import { useAuthStore } from '~/stores/auth'
import { useI18n } from '#imports'
import { useThemeStore } from '@/stores/useTheme'

const themeStore = useThemeStore()
const theme = useTheme()
const authStore = useAuthStore()
const { locale, setLocale } = useI18n()


onMounted(() => {
  themeStore.initialize()
  theme.global.name.value = themeStore.theme
})

const isDark = computed({
  get: () => themeStore.theme === 'dark',
  set: (value) => {
    const newTheme = value ? 'dark' : 'light'
    themeStore.setTheme(newTheme)
    theme.global.name.value = newTheme
    console.log('theme.global.name.value', theme.global.name.value)
  }
})

const loggedIn = computed(() => authStore.isAuthenticated)
const user = computed(() => authStore.user)
const defaultAvatar = 'https://upload.wikimedia.org/wikipedia/commons/8/89/Portrait_Placeholder.png'
const authLinks = [
  { titleKey: 'navigator.create_dataset', to: '/create_dataset', icon: 'mdi-plus-box' },
  { titleKey: 'navigator.datasets', to: '/datasets', icon: 'mdi-database' },
]
const guestLinks = [
  { titleKey: 'navigator.signup', to: '/', icon: 'mdi-login' }
]
const drawer = ref(true)
const rail = ref(true)

const langSwitch = ref(locale.value === 'en')
const currentLang = computed(() => locale.value)

watch(locale, (newLocale) => {
  langSwitch.value = newLocale === 'en'
})

const toggleLang = () => {
  const newLocale = locale.value === 'ru' ? 'en' : 'ru'
  setLocale(newLocale) 
}

const logout = async () => {
  try {
    await authStore.logout()
  } catch (error) {
    console.error('Logout error:', error)
  }
}



</script>

<style scoped>
.logout-btn {
  margin-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.text-error {
  color: #f44336 !important; 
}

.logout-btn:hover {
  background-color: rgba(244, 67, 54, 0.1) !important;
}
</style>