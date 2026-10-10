import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '总览' } },
  { path: '/chat', name: 'chat', component: () => import('../views/Chat.vue'), meta: { title: '面试间' } },
  { path: '/knowledge', name: 'knowledge', component: () => import('../views/Knowledge.vue'), meta: { title: '资料库' } },
  { path: '/report', name: 'report', component: () => import('../views/Report.vue'), meta: { title: '评估报告' } }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.afterEach(() => {
  document.title = '你的专属面试助手'
})

export default router
