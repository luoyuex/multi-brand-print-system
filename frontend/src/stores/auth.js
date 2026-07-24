import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, getToken, setToken } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(getToken())

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(username, password) {
    const res = await authApi.login({ username, password })
    token.value = res.token
    setToken(res.token)
    user.value = res.user
    return res.user
  }

  // 刷新页面后用已存的 token 拉当前用户；token 失效则清空
  async function fetchMe() {
    if (!token.value) return null
    try {
      user.value = await authApi.me()
      return user.value
    } catch (e) {
      logout()
      return null
    }
  }

  function logout() {
    token.value = null
    user.value = null
    setToken(null)
  }

  return { user, token, isLoggedIn, isAdmin, login, fetchMe, logout }
})
