import { defineStore } from 'pinia'
import { getToken } from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({ token: getToken() }),
  getters: {
    isLoggedIn: (s) => !!s.token,
  },
})
