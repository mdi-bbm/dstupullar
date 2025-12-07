import { defineStore } from 'pinia'

interface LoginResponse {
  access: string
  refresh: string
  user?: {
    id: number
    username: string
    email: string
  }
}

interface RefreshResponse {
  access: string
}

interface UserProfile {
  id: number
  username: string
  email: string
}

interface ProfileResponse {
  user: UserProfile  
}

interface RegisterResponse {
  message?: string
  success?: boolean
}

export const useAuthStore = defineStore('auth', () => {
  const token = useCookie<string | null>('auth_token', { 
    default: () => null,
    maxAge: 60 * 60 * 24, 
    secure: true,         
    sameSite: 'lax' 
  })
  
  const refreshTokenCookie = useCookie<string | null>('refresh_token', {
    default: () => null, 
    maxAge: 60 * 60 * 24 * 7, 
    secure: true,
    sameSite: 'lax'
  })
  
  const user = ref<UserProfile | null>(null)
  const isAuthenticated = computed(() => !!token.value)
  const isLoading = ref(false)
  const isRefreshing = ref(false)
  const refreshPromise = ref<Promise<string> | null>(null)


  const login = async (credentials: { username: string; password: string }) => {
    if (import.meta.client) {
      const allLegacyCookies = [
        'auth_token', 'refresh_token', 'csrftoken',
        'auth._token.local', 'auth._refresh_token.local',
        'auth._token_expiration.local', 'auth._refresh_token_expiration.local',
        'auth.strategy',
        'token', 'auth_token', 'authToken',
        'refresh_token', 'refreshToken',
        'sessionid', 'session_id'
      ]
      
      allLegacyCookies.forEach(name => {
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`
        document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`
      })
    }

    isLoading.value = true

    try {
      const config = useRuntimeConfig()
      const response = await $fetch<LoginResponse>('/api/token_9fqmnqe010opnsvq9ql/', {
        method: 'POST',
        body: credentials,
        baseURL: config.public.apiBase, 
        credentials: 'include'
      })
      
      token.value = response.access
      refreshTokenCookie.value = response.refresh 
      
      if (import.meta.client) {
        await fetchUserProfile()
      }
      
      return response
    } catch (error) {
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const refreshToken = async (): Promise<string> => {
    if (isRefreshing.value && refreshPromise.value) {
      return refreshPromise.value
    }

    if (!refreshTokenCookie.value) {
      throw new Error('No refresh token available')
    }

    isRefreshing.value = true

    try {
      const config = useRuntimeConfig()
      refreshPromise.value = $fetch<RefreshResponse>('/api/refresh_token_gn240202ns301f1/', {
        method: 'POST',
        body: {
          refresh: refreshTokenCookie.value
        },
        baseURL: config.public.apiBase, 
        credentials: 'include'
      }).then(response => {
        token.value = response.access
        return response.access
      })
      
      const newToken = await refreshPromise.value
      return newToken

    } catch (error: any) {
      if (error.status === 401 || error.status === 400) {
        logout()
      }
      
      throw new Error('Failed to refresh token')
    } finally {
      isRefreshing.value = false
      refreshPromise.value = null
    }
  }

  const register = async (userData: { username: string; password: string; confirmPassword: string }) => {
    isLoading.value = true
    
    try {
      const config = useRuntimeConfig()
      const response = await $fetch<RegisterResponse>('/api/register/', {
        method: 'POST',
        body: {
          username: userData.username,
          password: userData.password,
          password2: userData.confirmPassword
        },
        baseURL: config.public.apiBase, 
        credentials: 'include'
      })

      if (import.meta.client) {
        await login({
          username: userData.username,
          password: userData.password
        })
      }
      
      return response
    } catch (error) {
      throw error
    } finally {
      isLoading.value = false
    }
  }

  const fetchUserProfile = async () => {
    if (!token.value) return
    
    try {
      const config = useRuntimeConfig()
      const response = await $fetch<ProfileResponse>('/api/profile_18fn1038wn198r1nb/', {
        headers: {
          Authorization: `Bearer ${token.value}`
        },
        baseURL: config.public.apiBase, 
        credentials: 'include'
      })
      user.value = response.user
    } catch (error: any) {
      if (error.status === 401 && refreshTokenCookie.value) {
        try {
          await refreshToken()
          await fetchUserProfile() 
        } catch (refreshError) {
          logout()
        }
      } else {
        logout()
      }
    }
  }

  const logout = () => {
    token.value = null
    refreshTokenCookie.value = null 
    user.value = null
  }

  const checkAuth = async () => {
    if (!import.meta.client) return
    
    if (token.value) {
      try {
        await fetchUserProfile()
      } catch (error) {
        if (refreshTokenCookie.value) {
          try {
            await refreshToken()
            await fetchUserProfile() 
          } catch (refreshError) {
            logout() 
          }
        } else {
          logout() 
        }
      }
    }
  }

  return {
    token,
    user,
    isAuthenticated,
    isLoading,
    login,
    register,
    logout,
    checkAuth,
    fetchUserProfile,
    refreshToken 
  }
})