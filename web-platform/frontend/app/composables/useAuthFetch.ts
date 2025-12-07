export const useAuthFetch = () => {
  const authStore = useAuthStore()

  const baseAuthFetch = async (url: string, options: any = {}) => {
    if (import.meta.server) {
      return await $fetch(url, options)
    }
    
    try {
      const headers = {
        ...options.headers,
        Authorization: `Bearer ${authStore.token}`
      }
      
      const response = await $fetch(url, {
        ...options,
        headers, 
        credentials: 'include'
      })
      
      return response
      
    } catch (error: any) {
      if (error.status === 401 && authStore.token) {
        try {
          await authStore.refreshToken()
          
          const headers = {
            ...options.headers,
            Authorization: `Bearer ${authStore.token}`
          }
          
          return await $fetch(url, {
            ...options,
            headers, 
            credentials: 'include'
          })
          
        } catch (refreshError) {
          authStore.logout()
      
          throw new Error('Failed to refresh token')
        }
      }
      
      throw error
    }
  }

  const authGet = (url: string, options?: any) => 
    baseAuthFetch(url, { ...options, method: 'GET' })

  const authPost = (url: string, data?: any, options?: any) => 
    baseAuthFetch(url, { ...options, method: 'POST', body: data })

  const authPut = (url: string, data?: any, options?: any) => 
    baseAuthFetch(url, { ...options, method: 'PUT', body: data })

  const authPatch = (url: string, data?: any, options?: any) => 
    baseAuthFetch(url, { ...options, method: 'PATCH', body: data })

  const authDelete = (url: string, data?: any, options?: any) => 
    baseAuthFetch(url, { ...options, method: 'DELETE', body: data })

  const authUpload = (url: string, formData: FormData, options?: any) => 
    baseAuthFetch(url, { 
      ...options, 
      method: 'POST', 
      body: formData
    })

  return {
    authFetch: baseAuthFetch,
    authGet,
    authPost,
    authPut,
    authPatch,
    authDelete,
    authUpload
  }
}
