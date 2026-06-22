import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

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

  function setAuth(newToken: string, newUser: User) {
    token.value = newToken
    user.value = newUser
    localStorage.setItem(TOKEN_KEY, newToken)
    localStorage.setItem(USER_KEY, JSON.stringify(newUser))
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
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
    setAuth,
    logout,
    updateUser
  }
})
