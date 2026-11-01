import { defineStore } from 'pinia'
import { listPositions } from '../api'

export const CUSTOM_PREFIX = 'custom:'

export const ROLE_OPTIONS = [
  { id: 'technical', name: '专业技术面', desc: '项目深挖、技术原理与方案设计', icon: 'cpu' },
  { id: 'behavioral', name: '行为面', desc: 'STAR 法则考察协作、冲突与成长', icon: 'users' },
  { id: 'hr', name: 'HR 面', desc: '动机、稳定性、职业规划与期望', icon: 'user' }
]

export const ROLE_NAMES = Object.fromEntries(ROLE_OPTIONS.map((r) => [r.id, r.name]))

export const useCatalogStore = defineStore('catalog', {
  state: () => ({
    categories: [],
    positions: [],
    loaded: false,
    loading: false,
    error: ''
  }),
  getters: {
    positionMap: (s) => Object.fromEntries(s.positions.map((p) => [p.id, p])),
    categoryMap: (s) => Object.fromEntries(s.categories.map((c) => [c.id, c])),
    hotPositions: (s) => s.positions.filter((p) => p.hot)
  },
  actions: {
    async load(force = false) {
      if ((this.loaded && !force) || this.loading) return
      this.loading = true
      try {
        const data = await listPositions()
        this.categories = data.categories || []
        this.positions = data.positions || []
        this.loaded = true
        this.error = ''
      } catch (e) {
        this.error = e.message || '岗位目录加载失败'
      } finally {
        this.loading = false
      }
    },
    nameOf(direction) {
      if (!direction) return '未选择岗位'
      if (direction.startsWith(CUSTOM_PREFIX)) return direction.slice(CUSTOM_PREFIX.length) || '自定义岗位'
      return this.positionMap[direction]?.name || direction
    }
  }
})
