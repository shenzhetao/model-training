import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { clearRequestCache } from '@/api/request'

const TOKEN_KEY = 'gameassistant_token'
const USER_KEY = 'gameassistant_user'

export interface User {
  id: string
  username: string
  email?: string
  role: 'admin' | 'annotator' | 'reviewer'
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<User | null>(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const username = computed(() => user.value?.username || '')

  function setToken(newToken: string) {
    token.value = newToken
    localStorage.setItem(TOKEN_KEY, newToken)
  }

  function setUser(newUser: User | null) {
    user.value = newUser
    localStorage.setItem(USER_KEY, JSON.stringify(newUser))
  }

  function setAuth(newToken: string, newUser: User | null) {
    setToken(newToken)
    setUser(newUser)
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    // Clear request cache on logout
    clearRequestCache()
  }

  function updateUser(newUser: Partial<User>) {
    if (user.value) {
      user.value = { ...user.value, ...newUser }
      localStorage.setItem(USER_KEY, JSON.stringify(user.value))
    }
  }

  return {
    token,
    user,
    isAuthenticated,
    isAdmin,
    username,
    setToken,
    setUser,
    setAuth,
    logout,
    updateUser
  }
})
