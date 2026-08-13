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
app.use(createPinia())
app.use(router)
app.mount('#app')
