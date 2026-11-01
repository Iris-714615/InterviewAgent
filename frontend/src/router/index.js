import { createRouter, createWebHistory } from 'vue-router'
import { getToken } from '../api'

const seenLanding = () => {
  try { return !!localStorage.getItem('ia-seen-landing') } catch (e) { return true }
}

const routes = [
  { path: '/welcome', name: 'welcome', component: () => import('../views/Landing.vue'), meta: { title: '欢迎', bare: true } },
  { path: '/login', name: 'login', component: () => import('../views/Auth.vue'), meta: { title: '登录', bare: true } },
  { path: '/register', name: 'register', component: () => import('../views/Auth.vue'), meta: { title: '注册', bare: true } },
  { path: '/account', name: 'account', component: () => import('../views/Account.vue'), meta: { title: '我的账号', auth: true } },
  { path: '/resume', name: 'resume', component: () => import('../views/Resume.vue'), meta: { title: '简历工坊' } },
  { path: '/jobs', name: 'jobs', component: () => import('../views/Jobs.vue'), meta: { title: '求职看板', auth: true } },
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

router.beforeEach((to) => {
  if (to.meta?.auth && !getToken()) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'dashboard' && !getToken() && !seenLanding()) {
    return { path: '/welcome' }
  }
  return true
})

router.afterEach((to) => {
  document.title = to.meta?.title ? `${to.meta.title} · InterviewAgent` : 'InterviewAgent'
})

export default router
