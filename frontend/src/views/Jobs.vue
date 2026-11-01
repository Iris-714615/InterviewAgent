<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import Icon from '../components/Icon.vue'
import { listJobs, createJob, updateJob, deleteJob } from '../api'
import { PLATFORMS, platformUrl } from '../utils/platforms'
import { toast } from '../utils/toast'

const COLUMNS = [
  { id: 'wishlist', label: '意向', tone: 'info' },
  { id: 'applied', label: '已投递', tone: 'primary' },
  { id: 'interview', label: '面试中', tone: 'warning' },
  { id: 'offer', label: 'Offer', tone: 'success' },
  { id: 'rejected', label: '未通过', tone: '' },
]

const jobs = ref([])
const loading = ref(true)
const saving = ref(false)
const activeCol = ref('wishlist')
const drawerOpen = ref(false)
const editingId = ref(null)
const keyword = ref('')

const blank = () => ({
  company: '', title: '', status: 'wishlist', salary: '', location: '', url: '', note: '', jd_text: '',
})
const form = reactive(blank())

const grouped = computed(() => {
  const map = Object.fromEntries(COLUMNS.map((c) => [c.id, []]))
  for (const j of jobs.value) (map[j.status] || map.wishlist).push(j)
  return map
})

async function load() {
  loading.value = true
  try {
    const res = await listJobs()
    jobs.value = res.jobs || []
  } catch (e) {
    toast.error(e.message || '加载岗位失败')
  } finally {
    loading.value = false
  }
}

function openNew(status = 'wishlist') {
  editingId.value = null
  Object.assign(form, blank(), { status })
  drawerOpen.value = true
}

function openEdit(job) {
  editingId.value = job.id
  Object.assign(form, blank(), job)
  drawerOpen.value = true
}

async function save() {
  if (!form.company.trim() && !form.title.trim()) {
    toast.error('公司和岗位至少填写一项')
    return
  }
  saving.value = true
  try {
    const payload = { ...form }
    delete payload.id
    delete payload.created_at
    delete payload.updated_at
    if (editingId.value) {
      const res = await updateJob(editingId.value, payload)
      const i = jobs.value.findIndex((j) => j.id === editingId.value)
      if (i >= 0) jobs.value[i] = res.job
    } else {
      const res = await createJob(payload)
      jobs.value.unshift(res.job)
    }
    activeCol.value = form.status
    drawerOpen.value = false
    toast.success('已保存')
  } catch (e) {
    toast.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function move(job, status) {
  if (job.status === status) return
  const prev = job.status
  job.status = status
  try {
    await updateJob(job.id, { ...job, status })
  } catch (e) {
    job.status = prev
    toast.error(e.message || '更新失败')
  }
}

async function remove(job) {
  if (!window.confirm(`确定删除「${job.company || job.title}」吗?`)) return
  try {
    await deleteJob(job.id)
    jobs.value = jobs.value.filter((j) => j.id !== job.id)
    drawerOpen.value = false
    toast.success('已删除')
  } catch (e) {
    toast.error(e.message || '删除失败')
  }
}

function openPlatform(p) {
  window.open(platformUrl(p, keyword.value.trim() || form.title || ''), '_blank', 'noopener')
}

onMounted(load)
</script>

<template>
  <div class="jobs-page">
    <header class="page-head">
      <div>
        <h1 class="page-title">求职看板</h1>
        <p class="page-sub">记录每个目标岗位的进展,从意向到 Offer 一目了然</p>
      </div>
      <button class="btn btn-primary" @click="openNew()"><Icon name="plus" :size="16" /> 添加岗位</button>
    </header>

    <section class="card finder">
      <div class="finder-title"><Icon name="search" :size="16" /> 去招聘平台找岗位</div>
      <div class="finder-row">
        <input v-model="keyword" class="input" placeholder="输入岗位关键词,如:前端开发" />
        <div class="plats">
          <button v-for="p in PLATFORMS" :key="p.id" class="btn btn-secondary btn-sm" @click="openPlatform(p)">{{ p.name }}</button>
        </div>
      </div>
    </section>

    <div class="seg col-seg">
      <button v-for="c in COLUMNS" :key="c.id" :class="{ on: activeCol === c.id }" @click="activeCol = c.id">
        {{ c.label }} {{ grouped[c.id].length }}
      </button>
    </div>

    <div v-if="loading" class="empty"><span class="spinner" /></div>
    <div v-else class="board">
      <section v-for="c in COLUMNS" :key="c.id" class="col" :class="{ active: activeCol === c.id }">
        <div class="col-head">
          <span class="tag" :class="c.tone ? `tag-${c.tone}` : ''">{{ c.label }}</span>
          <span class="col-count">{{ grouped[c.id].length }}</span>
          <button class="btn btn-ghost btn-icon btn-sm" :aria-label="`新增${c.label}岗位`" @click="openNew(c.id)"><Icon name="plus" :size="14" /></button>
        </div>
        <div v-if="!grouped[c.id].length" class="col-empty">
          <Icon name="briefcase" :size="20" />
          <span>暂无岗位</span>
        </div>
        <article v-for="j in grouped[c.id]" :key="j.id" class="job" tabindex="0" @click="openEdit(j)" @keydown.enter="openEdit(j)">
          <div class="job-title truncate">{{ j.title || '未填写岗位' }}</div>
          <div class="job-company truncate">{{ j.company || '未填写公司' }}</div>
          <div class="job-meta">
            <span v-if="j.salary" class="tag tag-success">{{ j.salary }}</span>
            <span v-if="j.location" class="job-loc"><Icon name="flag" :size="12" /> {{ j.location }}</span>
          </div>
          <select class="job-move" :value="j.status" aria-label="更改状态" @click.stop @change="move(j, $event.target.value)">
            <option v-for="o in COLUMNS" :key="o.id" :value="o.id">{{ o.label }}</option>
          </select>
        </article>
      </section>
    </div>

    <transition name="fade">
      <div v-if="drawerOpen" class="overlay" @click="drawerOpen = false" />
    </transition>
    <transition name="drawer">
      <aside v-if="drawerOpen" class="drawer" aria-label="岗位详情">
        <div class="drawer-head">
          <h3 class="flex-1">{{ editingId ? '编辑岗位' : '添加岗位' }}</h3>
          <button class="btn btn-ghost btn-icon" aria-label="关闭" @click="drawerOpen = false"><Icon name="x" :size="16" /></button>
        </div>
        <div class="drawer-body form-grid">
          <label><span class="field-label">公司</span><input v-model="form.company" class="input" placeholder="公司名称" /></label>
          <label><span class="field-label">岗位</span><input v-model="form.title" class="input" placeholder="岗位名称" /></label>
          <label>
            <span class="field-label">状态</span>
            <select v-model="form.status" class="input">
              <option v-for="o in COLUMNS" :key="o.id" :value="o.id">{{ o.label }}</option>
            </select>
          </label>
          <label><span class="field-label">薪资</span><input v-model="form.salary" class="input" placeholder="如 20-30K" /></label>
          <label><span class="field-label">地点</span><input v-model="form.location" class="input" placeholder="城市" /></label>
          <label><span class="field-label">岗位链接</span><input v-model="form.url" class="input" placeholder="https://" /></label>
          <label class="full"><span class="field-label">备注</span><textarea v-model="form.note" class="textarea" rows="3" placeholder="面试时间、联系人等" /></label>
          <label class="full"><span class="field-label">JD 原文</span><textarea v-model="form.jd_text" class="textarea" rows="6" placeholder="粘贴岗位描述,可用于生成简历与模拟面试" /></label>
          <div v-if="editingId" class="full links">
            <a v-if="form.url" class="btn btn-secondary btn-sm" :href="form.url" target="_blank" rel="noopener">打开岗位链接</a>
            <router-link class="btn btn-secondary btn-sm" to="/resume">去做定向简历</router-link>
            <router-link class="btn btn-secondary btn-sm" to="/chat">模拟面试</router-link>
          </div>
        </div>
        <div class="drawer-foot">
          <button v-if="editingId" class="btn btn-ghost" @click="remove(jobs.find((j) => j.id === editingId))"><Icon name="trash" :size="14" /> 删除</button>
          <span class="flex-1" />
          <button class="btn btn-secondary" @click="drawerOpen = false">取消</button>
          <button class="btn btn-primary" :disabled="saving" @click="save"><span v-if="saving" class="spinner" /> 保存</button>
        </div>
      </aside>
    </transition>
  </div>
</template>

<style scoped>
.finder { padding: 16px; margin-bottom: 18px; }
.finder-title { display: flex; align-items: center; gap: 6px; font-weight: 600; margin-bottom: 10px; color: var(--text); }
.finder-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
.finder-row .input { flex: 1; min-width: 200px; }
.plats { display: flex; gap: 8px; flex-wrap: wrap; }

.col-seg { display: none; margin-bottom: 14px; overflow-x: auto; }
.board { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; align-items: start; }
.col { background: var(--bg-soft); border: 1px solid var(--border); border-radius: var(--radius); padding: 10px; min-height: 160px; }
.col-head { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.col-count { color: var(--text-dim); font-size: 13px; flex: 1; }
.col-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 28px 0; color: var(--text-dim); font-size: 13px; }

.job { position: relative; background: var(--bg-card); border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 12px; margin-bottom: 10px; cursor: pointer; transition: border-color var(--dur) var(--ease), box-shadow var(--dur) var(--ease); }
.job:hover, .job:focus-visible { border-color: var(--primary-border); box-shadow: var(--shadow-soft); outline: none; }
.job-title { font-weight: 600; color: var(--text); }
.job-company { color: var(--text-soft); font-size: 13px; margin-top: 2px; }
.job-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 8px; }
.job-loc { display: inline-flex; align-items: center; gap: 3px; color: var(--text-dim); font-size: 12px; }
.job-move { margin-top: 10px; width: 100%; font-size: 12px; padding: 4px 6px; border-radius: var(--radius-xs); border: 1px solid var(--border); background: var(--bg-input); color: var(--text-soft); }

.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; align-content: start; }
.form-grid label { display: block; }
.form-grid .full { grid-column: 1 / -1; }
.links { display: flex; gap: 8px; flex-wrap: wrap; }

@media (max-width: 1100px) {
  .board { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
@media (max-width: 768px) {
  .col-seg { display: flex; }
  .board { grid-template-columns: 1fr; }
  .col { display: none; }
  .col.active { display: block; }
  .form-grid { grid-template-columns: 1fr; }
  .finder-row .input { min-width: 0; width: 100%; }
}
</style>
