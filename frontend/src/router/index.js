import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', name: 'dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '工作台' } },
  { path: '/chat', name: 'chat', component: () => import('../views/Chat.vue'), meta: { title: '模拟面试', flush: true } },
  { path: '/questions', name: 'questions', component: () => import('../views/QuestionBank.vue'), meta: { title: '面试题库' } },
  { path: '/knowledge', name: 'knowledge', component: () => import('../views/Knowledge.vue'), meta: { title: '资料库' } },
  { path: '/report', name: 'report', component: () => import('../views/Report.vue'), meta: { title: '评估报告' } },
  { path: '/:pathMatch(.*)*', redirect: '/' }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

router.afterEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} · InterviewAgent` : 'InterviewAgent'
})

export default router
