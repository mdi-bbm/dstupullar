<template>
  <div>
    <NuxtLayout>
        <NuxtPage />
    </NuxtLayout>
  </div>
</template>

<script setup>
const authStore = useAuthStore()


onMounted(() => {
  if (authStore.token) {
    authStore.checkAuth()
  }
  
  watch(() => authStore.isAuthenticated, (isAuthenticated) => {
    if (!isAuthenticated && window.location.pathname !== '/') {
      navigateTo('/')
    }
    
    if (isAuthenticated && window.location.pathname === '/') {
      navigateTo('/datasets')
    }
})
})
</script>