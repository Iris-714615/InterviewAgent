<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const theme = ref('dark')
const navs = [
  { name: 'dashboard', path: '/', icon: '🎯', label: '总览' },
  { name: 'chat', path: '/chat', icon: '💬', label: '面试间' },
  { name: 'knowledge', path: '/knowledge', icon: '📚', label: '资料库' },
  { name: 'report', path: '/report', icon: '📊', label: '评估报告' }
]
const current = computed(() => route.name)

onMounted(() => {
  const savedTheme = localStorage.getItem('interview-agent-theme')
  if (savedTheme === 'light' || savedTheme === 'dark') theme.value = savedTheme
})

watch(theme, (value) => {
  document.documentElement.dataset.theme = value
  localStorage.setItem('interview-agent-theme', value)
}, { immediate: true })

function toggleTheme() {
  theme.value = theme.value === 'dark' ? 'light' : 'dark'
}
</script>

<template>
  <div class="layout">
    <!-- PC 侧边栏 -->
    <aside class="sidebar">
      <div class="logo">
        <img class="logo-icon" src="/favicon.svg" alt="" />
        <span>你的专属面试助手</span>
      </div>
      <button
        class="theme-toggle"
        type="button"
        :aria-label="theme === 'dark' ? '切换到白天模式' : '切换到夜晚模式'"
        @click="toggleTheme"
      >
        <span aria-hidden="true">{{ theme === 'dark' ? '☀️' : '🌙' }}</span>
        <span>{{ theme === 'dark' ? '白天模式' : '夜晚模式' }}</span>
      </button>
      <router-link
        v-for="n in navs"
        :key="n.name"
        :to="n.path"
        class="nav-item"
        :class="{ active: current === n.name }"
      >
        <span class="icon">{{ n.icon }}</span>
        <span>{{ n.label }}</span>
      </router-link>
    </aside>

    <!-- 主内容 -->
    <main class="main">
      <header class="topbar">
        <span class="topbar-label">你的专属面试助手</span>
        <button
          class="theme-toggle theme-toggle-mobile"
          type="button"
          :aria-label="theme === 'dark' ? '切换到白天模式' : '切换到夜晚模式'"
          @click="toggleTheme"
        >
          <span aria-hidden="true">{{ theme === 'dark' ? '☀️' : '🌙' }}</span>
          <span>{{ theme === 'dark' ? '白天' : '夜晚' }}</span>
        </button>
      </header>
      <div class="content">
        <router-view />
      </div>
    </main>

    <!-- 手机底部导航 -->
    <nav class="bottom-nav">
      <router-link
        v-for="n in navs"
        :key="n.name"
        :to="n.path"
        class="nav-item"
        :class="{ active: current === n.name }"
      >
        <span class="icon">{{ n.icon }}</span>
        <span>{{ n.label }}</span>
      </router-link>
    </nav>
  </div>
</template>
