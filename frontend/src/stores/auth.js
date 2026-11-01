import { defineStore } from 'pinia'
import {
  getToken,
  setToken,
  setUnauthorizedHandler,
  login as apiLogin,
  register as apiRegister,
  fetchMe,
  updateMe,
  deleteMe,
} from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({ token: getToken(), user: null }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    displayName: (s) => s.user?.nickname || s.user?.email?.split('@')[0] || '未登录',
  },
  actions: {
    _apply(res) {
      this.token = res.token
      this.user = res.user
      setToken(res.token)
    },
    async login(email, password) {
      this._apply(await apiLogin(email, password))
    },
    async register(email, password, nickname) {
      this._apply(await apiRegister(email, password, nickname))
    },
    async load() {
      if (!this.token || this.user) return
      try {
        const res = await fetchMe()
        this.user = res.user || res
      } catch {
        /* 401 由全局回调处理 */
      }
    },
    async update(payload) {
      const res = await updateMe(payload)
      this.user = res.user || res
    },
    logout() {
      this.token = ''
      this.user = null
      setToken('')
    },
    async remove() {
      await deleteMe()
      this.logout()
    },
    bindUnauthorized(onExpire) {
      setUnauthorizedHandler(() => {
        this.logout()
        onExpire?.()
      })
    },
  },
})
