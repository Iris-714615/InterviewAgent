<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter, RouterLink } from 'vue-router'
import Icon from '../components/Icon.vue'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const isRegister = computed(() => route.name === 'register')
const email = ref('')
const password = ref('')
const nickname = ref('')
const loading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  if (!/^\S+@\S+\.\S+$/.test(email.value)) return (error.value = '请输入有效的邮箱')
  if (password.value.length < 6) return (error.value = '密码至少 6 位')
  loading.value = true
  try {
    if (isRegister.value) await auth.register(email.value, password.value, nickname.value.trim())
    else await auth.login(email.value, password.value)
    router.replace(route.query.redirect || '/')
  } catch (e) {
    error.value = e.message || '操作失败，请稍后重试'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <form class="auth-card card" @submit.prevent="submit">
      <RouterLink to="/welcome" class="auth-brand">
        <Icon name="logo" :size="22" />
        <span>InterviewAgent</span>
      </RouterLink>
      <h1>{{ isRegister ? '创建账号' : '欢迎回来' }}</h1>
      <p class="sub">{{ isRegister ? '保存简历、追踪投递，让求职有迹可循' : '登录后同步你的简历与投递进度' }}</p>

      <label v-if="isRegister" class="field">
        <span class="field-label">昵称（选填）</span>
        <input v-model="nickname" class="input" maxlength="20" autocomplete="nickname" placeholder="怎么称呼你" />
      </label>
      <label class="field">
        <span class="field-label">邮箱</span>
        <input v-model="email" class="input" type="email" autocomplete="email" placeholder="you@example.com" />
      </label>
      <label class="field">
        <span class="field-label">密码</span>
        <input
          v-model="password"
          class="input"
          type="password"
          :autocomplete="isRegister ? 'new-password' : 'current-password'"
          placeholder="至少 6 位"
        />
      </label>

      <div v-if="error" class="alert alert-danger" role="alert">{{ error }}</div>

      <button class="btn btn-primary btn-lg btn-block" :disabled="loading">
        <span v-if="loading" class="spinner"></span>
        {{ isRegister ? '注册并开始' : '登录' }}
      </button>

      <p class="switch">
        <template v-if="isRegister">已有账号？<RouterLink to="/login">去登录</RouterLink></template>
        <template v-else>还没有账号？<RouterLink to="/register">免费注册</RouterLink></template>
      </p>
      <RouterLink to="/" class="skip">先逛逛，暂不登录</RouterLink>
    </form>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: 100dvh;
  display: grid;
  place-items: center;
  padding: 24px 16px;
  background: var(--bg);
}
.auth-card {
  width: 100%;
  max-width: 400px;
  padding: 32px 28px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.auth-brand {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: var(--text);
  text-decoration: none;
}
h1 { margin: 6px 0 0; font-size: 24px; color: var(--text); }
.sub { margin: 0 0 6px; color: var(--text-soft); font-size: 14px; }
.field { display: flex; flex-direction: column; gap: 6px; }
.input {
  width: 100%;
  padding: 11px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-input);
  color: var(--text);
  font: inherit;
  transition: border-color var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}
.input:focus { outline: none; border-color: var(--primary); box-shadow: 0 0 0 3px var(--primary-soft); }
.switch { margin: 4px 0 0; text-align: center; font-size: 14px; color: var(--text-soft); }
.switch a { color: var(--primary); font-weight: 600; margin-left: 4px; }
.skip { text-align: center; font-size: 13px; color: var(--text-dim); }
@media (max-width: 480px) {
  .auth-card { padding: 24px 18px; }
}
</style>
