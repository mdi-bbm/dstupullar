export default defineNuxtRouteMiddleware(async (to) => {
  if (import.meta.server && to.path.includes('/')) {
    return
  }
  
  const authStore = useAuthStore()
  
  try {
    await authStore.checkAuth()
  } catch (error) {
    console.error('Auth check failed:', error)
  }
  
  const requiresAuth = to.meta.requiresAuth as boolean | undefined
  
  if (requiresAuth && !authStore.isAuthenticated) {
    return navigateTo('/')
  }
  
  if (authStore.isAuthenticated && to.path === '/') {
    return navigateTo('/datasets')
  }
})