import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './styles/main.css'

// 开发环境清除旧的 Service Worker,避免拦截 SSE 流式请求
if (import.meta.env.DEV && 'serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then((regs) => {
    regs.forEach((reg) => reg.unregister())
  })
}

const app = createApp(App)

// 全局兜底:组件内未捕获的错误只记录,不让页面白屏
app.config.errorHandler = (err, _instance, info) => {
  console.error('[app error]', info, err)
}
window.addEventListener('unhandledrejection', (e) => {
  console.error('[unhandled rejection]', e.reason)
  e.preventDefault()
})

app.use(createPinia())
app.use(router)

// 懒加载页面 chunk 加载失败(常见于发版后旧页面):刷新一次获取最新资源
router.onError((err, to) => {
  const msg = String(err?.message || '')
  if (/Failed to fetch dynamically imported module|Importing a module script failed|Loading chunk/i.test(msg)) {
    const key = 'interview-agent-chunk-reload'
    if (!sessionStorage.getItem(key)) {
      sessionStorage.setItem(key, '1')
      window.location.assign(to?.fullPath || '/')
      return
    }
  }
  console.error('[router error]', err)
})
router.isReady().then(() => sessionStorage.removeItem('interview-agent-chunk-reload')).catch(() => {})

app.mount('#app')
