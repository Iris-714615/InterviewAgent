<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import Icon from './components/Icon.vue'
import { useChatStore } from './stores/chat'
import { toasts, dismissToast } from './utils/toast'

const route = useRoute()
const chat = useChatStore()
const stored = localStorage.getItem('interview-agent-theme')
const prefersLight = window.matchMedia?.('(prefers-color-scheme: light)').matches
const theme = ref(stored === 'light' || stored === 'dark' ? stored : prefersLight ? 'light' : 'dark')

const navs = [
  { name: 'dashboard', path: '/', icon: 'home', label: '工作台' },
  { name: 'chat', path: '/chat', icon: 'message', label: '模拟面试' },
  { name: 'questions', path: '/questions', icon: 'library', label: '面试题库' },
  { name: 'knowledge', path: '/knowledge', icon: 'folder', label: '资料库' },
  { name: 'report', path: '/report', icon: 'report', label: '评估报告' }
]
const current = computed(() => route.name)
const flush = computed(() => route.meta?.flush)

const service = computed(() => {
  if (chat.serviceStatusError) return { dot: 'dot-warning', text: '基础练习模式' }
  if (!chat.serviceStatus) return { dot: '', text: '正在检测服务' }
  if (chat.serviceStatus.demo_mode) return { dot: 'dot-warning', text: '演示模式' }
  if (chat.serviceStatus.status === 'ok') return { dot: 'dot-success', text: '服务运行正常' }
  if (chat.serviceStatus.api_key_configured === false) return { dot: 'dot-warning', text: '本地练习模式' }
  return { dot: 'dot-warning', text: '服务降级运行' }
})

watch(theme, (value) => {
  document.documentElement.dataset.theme = value
  localStorage.setItem('interview-agent-theme', value)
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content', value === 'dark' ? '#000000' : '#fff8fa')
}, { immediate: true })

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}

onMounted(() => {
  if (!chat.serviceStatus) chat.loadServiceStatus()
})
</script>

<template>
  <div class="layout">
    <aside class="sidebar" aria-label="主导航">
      <router-link to="/" class="brand">
        <span class="brand-mark"><Icon name="sparkle4" :size="18" /></span>
        <span>
          <div class="brand-name">InterviewAgent</div>
          <div class="brand-sub">AI 模拟面试 · 智能陪练</div>
        </span>
      </router-link>

      <router-link to="/chat" class="btn btn-primary btn-block mb-2">
        <Icon name="plus" :size="16" :stroke="2.2" />新建模拟面试
      </router-link>

      <nav class="nav-group">
        <div class="nav-label">导航</div>
        <router-link
          v-for="n in navs"
          :key="n.name"
          :to="n.path"
          class="nav-item"
          :class="{ active: current === n.name }"
          :aria-current="current === n.name ? 'page' : undefined"
        >
          <Icon class="nav-icon" :name="n.icon" :size="18" />
          <span>{{ n.label }}</span>
          <span v-if="n.name === 'chat' && chat.streaming" class="nav-badge dot dot-success dot-pulse"></span>
        </router-link>
      </nav>

      <div class="sidebar-foot">
        <div class="status-pill" role="status">
          <span class="dot" :class="service.dot"></span>
          <span class="flex-1 truncate">{{ service.text }}</span>
        </div>
        <button class="nav-item" type="button" @click="toggleTheme" :aria-label="theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'">
          <Icon class="nav-icon" :name="theme === 'dark' ? 'sun' : 'moon'" :size="18" />
          <span>{{ theme === 'dark' ? '浅色模式' : '深色模式' }}</span>
        </button>
      </div>
    </aside>

    <main class="main">
      <header class="topbar">
        <router-link to="/" class="row" style="color: var(--text)">
          <span class="brand-mark" style="width: 28px; height: 28px; border-radius: 8px"><Icon name="sparkle4" :size="15" /></span>
          <strong>{{ route.meta?.title || 'InterviewAgent' }}</strong>
        </router-link>
        <div class="row gap-1">
          <span class="dot" :class="service.dot" :title="service.text"></span>
          <button class="btn btn-ghost btn-icon btn-sm" type="button" @click="toggleTheme" :aria-label="theme === 'dark' ? '切换到浅色模式' : '切换到深色模式'">
            <Icon :name="theme === 'dark' ? 'sun' : 'moon'" :size="18" />
          </button>
        </div>
      </header>
      <div class="content" :class="{ flush }">
        <router-view v-slot="{ Component }">
          <transition name="page">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>

    <nav class="bottom-nav" aria-label="底部导航">
      <router-link
        v-for="n in navs"
        :key="n.name"
        :to="n.path"
        class="nav-item"
        :class="{ active: current === n.name }"
      >
        <Icon :name="n.icon" :size="21" />
        <span>{{ n.label }}</span>
      </router-link>
    </nav>

    <div class="toast-stack" aria-live="polite">
      <div v-for="t in toasts" :key="t.id" class="toast" :class="`toast-${t.type}`" @click="dismissToast(t.id)">
        <Icon class="alert-icon" :name="t.type === 'success' ? 'checkCircle' : t.type === 'error' ? 'xCircle' : 'info'" :size="17" />
        <span class="flex-1">{{ t.message }}</span>
      </div>
    </div>
  </div>
</template>
