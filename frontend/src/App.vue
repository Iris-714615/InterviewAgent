<script setup>
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()
const navs = [
  { name: 'dashboard', path: '/', icon: '🎯', label: '总览' },
  { name: 'chat', path: '/chat', icon: '💬', label: '面试间' },
  { name: 'knowledge', path: '/knowledge', icon: '📚', label: '资料库' },
  { name: 'report', path: '/report', icon: '📊', label: '评估报告' }
]
const current = computed(() => route.name)
</script>

<template>
  <div class="layout">
    <!-- PC 侧边栏 -->
    <aside class="sidebar">
      <div class="logo">
        <span class="logo-icon">面</span>
        <span>面试私教</span>
      </div>
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
