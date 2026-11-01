<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import { useAuthStore } from '../stores/auth'
import { listSavedResumes, deleteSavedResume } from '../api'
import { toast } from '../utils/toast'

const auth = useAuthStore()
const router = useRouter()

const nickname = ref(auth.user?.nickname || '')
const targetRole = ref(auth.user?.target_role || '')
const saving = ref(false)
const items = ref([])
const loading = ref(true)

async function loadItems() {
  loading.value = true
  try {
    const res = await listSavedResumes()
    items.value = res.items || []
  } catch (e) {
    toast.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  saving.value = true
  try {
    await auth.update({ nickname: nickname.value.trim(), target_role: targetRole.value.trim() })
    toast.success('资料已更新')
  } catch (e) {
    toast.error(e.message || '更新失败')
  } finally {
    saving.value = false
  }
}

async function removeItem(it) {
  if (!confirm(`确定删除简历「${it.title || '未命名'}」?`)) return
  try {
    await deleteSavedResume(it.id)
    items.value = items.value.filter((x) => x.id !== it.id)
    toast.success('已删除')
  } catch (e) {
    toast.error(e.message || '删除失败')
  }
}

function logout() {
  auth.logout()
  router.replace('/welcome')
}

async function destroy() {
  if (!confirm('注销后账号、已保存简历与岗位将被永久删除,确定继续?')) return
  try {
    await auth.remove()
    toast.success('账号已注销')
    router.replace('/welcome')
  } catch (e) {
    toast.error(e.message || '注销失败')
  }
}

function fmt(t) {
  if (!t) return ''
  const d = new Date(typeof t === 'number' && t < 1e12 ? t * 1000 : t)
  return isNaN(d) ? '' : d.toLocaleDateString('zh-CN')
}

onMounted(async () => {
  await auth.load()
  nickname.value = auth.user?.nickname || ''
  targetRole.value = auth.user?.target_role || ''
  loadItems()
})
</script>

<template>
  <div class="acc">
    <section class="card acc-card">
      <div class="acc-head">
        <div class="acc-avatar">{{ (auth.displayName || 'U').slice(0, 1).toUpperCase() }}</div>
        <div class="flex-1">
          <h2>{{ auth.displayName }}</h2>
          <p class="acc-mail"><Icon name="mail" :size="14" />{{ auth.user?.email }}</p>
        </div>
      </div>
      <label class="field">
        <span class="field-label">昵称</span>
        <input v-model="nickname" class="input" maxlength="20" />
      </label>
      <label class="field">
        <span class="field-label">目标岗位</span>
        <input v-model="targetRole" class="input" maxlength="40" placeholder="如 前端开发工程师" />
      </label>
      <div class="row gap-1">
        <button class="btn btn-primary" :disabled="saving" @click="saveProfile">
          <span v-if="saving" class="spinner"></span>保存资料
        </button>
        <button class="btn btn-secondary" @click="logout"><Icon name="logout" :size="14" />退出登录</button>
      </div>
    </section>

    <section class="card acc-card">
      <div class="acc-sec-head">
        <h3><Icon name="fileText" :size="16" />我的简历</h3>
        <button class="btn btn-ghost btn-sm" @click="router.push('/resume')"><Icon name="plus" :size="14" />新建</button>
      </div>
      <div v-if="loading" class="skeleton" style="height: 64px"></div>
      <div v-else-if="!items.length" class="empty">
        <div class="empty-icon"><Icon name="fileText" :size="22" /></div>
        <p>还没有保存的简历,去生成一份吧</p>
      </div>
      <ul v-else class="acc-list">
        <li v-for="it in items" :key="it.id" class="acc-item">
          <button class="acc-main" @click="router.push({ path: '/resume', query: { load: it.id } })">
            <b class="truncate">{{ it.title || '未命名简历' }}</b>
            <span class="acc-meta">{{ it.template }} · {{ fmt(it.updated_at || it.created_at) }}</span>
          </button>
          <button class="btn btn-ghost btn-icon" aria-label="删除" @click="removeItem(it)"><Icon name="trash" :size="16" /></button>
        </li>
      </ul>
    </section>

    <section class="card acc-card acc-danger">
      <h3><Icon name="alert" :size="16" />危险操作</h3>
      <p>注销账号将永久删除所有数据,无法恢复。</p>
      <button class="btn btn-secondary" @click="destroy">注销账号</button>
    </section>
  </div>
</template>

<style scoped>
.acc { max-width: 720px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
.acc-card { padding: 20px; display: flex; flex-direction: column; gap: 14px; }
.acc-head { display: flex; align-items: center; gap: 14px; }
.acc-head h2 { margin: 0; font-size: 18px; }
.acc-mail { margin: 2px 0 0; display: flex; align-items: center; gap: 4px; font-size: 13px; color: var(--text-soft); }
.acc-avatar { width: 52px; height: 52px; border-radius: 50%; display: grid; place-items: center; font-size: 20px; font-weight: 700; color: var(--text-on-primary); background: var(--gradient-primary, var(--primary)); }
.field { display: flex; flex-direction: column; gap: 6px; }
.acc-sec-head { display: flex; align-items: center; justify-content: space-between; }
.acc-sec-head h3, .acc-danger h3 { margin: 0; font-size: 15px; display: flex; align-items: center; gap: 6px; }
.acc-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.acc-item { display: flex; align-items: center; gap: 6px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg-soft); padding-right: 6px; }
.acc-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; text-align: left; padding: 12px; background: none; border: 0; color: var(--text); cursor: pointer; }
.acc-meta { font-size: 12px; color: var(--text-dim); }
.acc-danger p { margin: 0; font-size: 13px; color: var(--text-soft); }
.acc-danger h3 { color: var(--danger); }
</style>
