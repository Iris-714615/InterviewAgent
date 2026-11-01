<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import { useCatalogStore } from '../stores/catalog'
import { addPractice, getQuestion, getQuestionsMeta, listQuestions, randomQuestions, setFavorite } from '../api'
import { toast } from '../utils/toast'

const router = useRouter()
const catalog = useCatalogStore()

const PAGE_SIZE = 20
const TYPE_OPTIONS = [
  { id: '', name: '全部' },
  { id: 'technical', name: '专业技术' },
  { id: 'behavioral', name: '行为面' },
  { id: 'hr', name: 'HR 面' }
]
const DIFFICULTY_OPTIONS = [
  { id: '', name: '全部' },
  { id: 'easy', name: '基础' },
  { id: 'medium', name: '进阶' },
  { id: 'hard', name: '挑战' }
]
const DIFFICULTY_TONE = { easy: 'success', medium: 'warning', hard: 'danger' }
const TYPE_TONE = { technical: 'primary', behavioral: 'info', hr: 'coach' }

const meta = ref(null)
const items = ref([])
const total = ref(0)
const loading = ref(false)
const error = ref('')

const filters = ref({ category: '', position: '', type: '', difficulty: '', keyword: '', tag: '', favorite: false })
const keywordInput = ref('')
const page = ref(1)
const showAllTags = ref(false)

const categories = computed(() => {
  const counts = meta.value?.by_category || {}
  const list = catalog.categories.map((c) => ({ id: c.id, name: c.name, count: counts[c.id] || 0 }))
  if (counts.general) list.push({ id: 'general', name: '通用', count: counts.general })
  return list.filter((c) => c.count > 0)
})
const positionOptions = computed(() => {
  const list = filters.value.category
    ? catalog.positions.filter((p) => p.category === filters.value.category)
    : catalog.positions
  return list
})
const tags = computed(() => {
  const all = meta.value?.tags || []
  return showAllTags.value ? all : all.slice(0, 16)
})
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const hasFilters = computed(() => Object.values(filters.value).some(Boolean))
const pageNumbers = computed(() => {
  const n = totalPages.value
  const cur = page.value
  const set = new Set([1, n, cur, cur - 1, cur + 1, cur - 2, cur + 2].filter((x) => x >= 1 && x <= n))
  const sorted = [...set].sort((a, b) => a - b)
  const out = []
  sorted.forEach((x, i) => {
    if (i && x - sorted[i - 1] > 1) out.push('…')
    out.push(x)
  })
  return out
})

async function loadMeta() {
  try {
    meta.value = await getQuestionsMeta()
  } catch (e) {
    toast.error(e.message)
  }
}

let reqId = 0
async function loadList() {
  const id = ++reqId
  loading.value = true
  error.value = ''
  try {
    const data = await listQuestions({ ...filters.value, page: page.value, page_size: PAGE_SIZE })
    if (id !== reqId) return
    items.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    if (id !== reqId) return
    error.value = e.message
  } finally {
    if (id === reqId) loading.value = false
  }
}

watch(filters, () => {
  if (page.value !== 1) page.value = 1
  else loadList()
}, { deep: true })
watch(page, () => {
  loadList()
  window.scrollTo({ top: 0, behavior: 'smooth' })
})
watch(() => filters.value.category, () => {
  if (filters.value.position && !positionOptions.value.some((p) => p.id === filters.value.position)) {
    filters.value.position = ''
  }
})

let debounce = null
watch(keywordInput, (v) => {
  clearTimeout(debounce)
  debounce = setTimeout(() => { filters.value.keyword = v.trim() }, 300)
})

function resetFilters() {
  keywordInput.value = ''
  filters.value = { category: '', position: '', type: '', difficulty: '', keyword: '', tag: '', favorite: false }
}
function toggleTag(name) {
  filters.value.tag = filters.value.tag === name ? '' : name
}

// ============ 收藏 ============
async function toggleFavorite(q) {
  const next = !q.favorite
  q.favorite = next
  if (detail.value?.id === q.id) detail.value.favorite = next
  try {
    await setFavorite(q.id, next)
    if (meta.value) meta.value.favorite_count += next ? 1 : -1
    toast.success(next ? '已加入收藏' : '已取消收藏')
    if (filters.value.favorite && !next) loadList()
  } catch (e) {
    q.favorite = !next
    if (detail.value?.id === q.id) detail.value.favorite = !next
    toast.error(e.message)
  }
}

// ============ 详情抽屉 ============
const detail = ref(null)
const detailLoading = ref(false)
const drawerOpen = ref(false)
const answer = ref('')
const rating = ref(0)
const submitting = ref(false)
const showOutline = ref(false)

async function openDetail(q) {
  drawerOpen.value = true
  detail.value = { ...q, practices: [] }
  answer.value = ''
  rating.value = 0
  showOutline.value = false
  detailLoading.value = true
  try {
    detail.value = await getQuestion(q.id)
  } catch (e) {
    toast.error(e.message)
  } finally {
    detailLoading.value = false
  }
}
function closeDetail() {
  drawerOpen.value = false
}

async function submitPractice() {
  const text = answer.value.trim()
  if (!text || !detail.value) return
  submitting.value = true
  try {
    const rec = await addPractice(detail.value.id, { answer: text, self_rating: rating.value || null })
    detail.value.practices = [rec, ...(detail.value.practices || [])]
    detail.value.practice_count = (detail.value.practice_count || 0) + 1
    const row = items.value.find((x) => x.id === detail.value.id)
    if (row) row.practice_count = detail.value.practice_count
    answer.value = ''
    rating.value = 0
    showOutline.value = true
    loadMeta()
    toast.success('练习已保存，对照答题思路复盘一下吧')
  } catch (e) {
    toast.error(e.message)
  } finally {
    submitting.value = false
  }
}

function practiceInterview(q) {
  const position = filters.value.position || q.positions?.[0] || catalog.hotPositions[0]?.id || ''
  router.push({ path: '/chat', query: { position, role: q.type, question: q.title } })
}

// ============ 随机抽题 ============
const randomOpen = ref(false)
const randomItems = ref([])
const randomLoading = ref(false)
async function drawRandom() {
  randomOpen.value = true
  randomLoading.value = true
  try {
    const data = await randomQuestions({
      count: 5,
      position: filters.value.position,
      type: filters.value.type,
      difficulty: filters.value.difficulty
    })
    randomItems.value = data.items || []
  } catch (e) {
    toast.error(e.message)
  } finally {
    randomLoading.value = false
  }
}
function openFromRandom(q) {
  randomOpen.value = false
  openDetail(q)
}

function formatTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function onKey(e) {
  if (e.key === 'Escape') {
    if (drawerOpen.value) closeDetail()
    else if (randomOpen.value) randomOpen.value = false
  }
}

onMounted(() => {
  catalog.load()
  loadMeta()
  loadList()
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  clearTimeout(debounce)
  window.removeEventListener('keydown', onKey)
})
</script>

<template>
  <div class="container qb">
    <header class="page-head row wrap gap-3">
      <div class="flex-1">
        <div class="eyebrow"><Icon name="library" :size="14" /> 题库中心</div>
        <h1 class="page-title">面试题库</h1>
        <p class="page-sub">覆盖 AI、后端、前端、数据、基础设施、产品与职能等方向，支持按岗位、题型、难度精准筛选，练完即可一键进入模拟面试。</p>
      </div>
      <div class="row gap-2">
        <button class="btn btn-secondary" @click="drawRandom"><Icon name="shuffle" :size="16" /> 随机抽题</button>
        <button class="btn btn-gradient" @click="router.push('/chat')"><Icon name="play" :size="16" /> 开始模拟面试</button>
      </div>
    </header>

    <section class="grid grid-4 stats">
      <div class="card stat">
        <div class="stat-label"><span class="stat-ico"><Icon name="layers" :size="14" /></span>题目总数</div>
        <div class="stat-value">{{ meta?.total ?? '—' }}</div>
        <div class="stat-foot text-dim">{{ categories.length }} 个方向</div>
      </div>
      <div class="card stat">
        <div class="stat-label"><span class="stat-ico"><Icon name="star" :size="14" /></span>我的收藏</div>
        <div class="stat-value">{{ meta?.favorite_count ?? '—' }}</div>
        <div class="stat-foot text-dim">重点题目反复打磨</div>
      </div>
      <div class="card stat">
        <div class="stat-label"><span class="stat-ico is-success"><Icon name="checkCircle" :size="14" /></span>已练习题目</div>
        <div class="stat-value">{{ meta?.practiced_questions ?? '—' }}</div>
        <div class="progress mt-2">
          <span :style="{ width: meta?.total ? `${Math.min(100, (meta.practiced_questions / meta.total) * 100)}%` : '0%' }" />
        </div>
      </div>
      <div class="card stat">
        <div class="stat-label"><span class="stat-ico is-info"><Icon name="history" :size="14" /></span>累计练习</div>
        <div class="stat-value">{{ meta?.practice_total ?? '—' }}<small class="text-dim text-sm"> 次</small></div>
        <div class="stat-foot text-dim">每次作答都会被记录</div>
      </div>
    </section>

    <section class="card filters mt-4">
      <div class="row wrap gap-3">
        <div class="input-group flex-1 search">
          <Icon class="icon-lead" name="search" :size="16" />
          <input v-model="keywordInput" class="input" placeholder="搜索题目、要点或标签，例如：RAG、索引、冲突" aria-label="搜索题目" />
        </div>
        <select v-model="filters.position" class="select pos-select" aria-label="按岗位筛选">
          <option value="">全部岗位</option>
          <option v-for="p in positionOptions" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
        <button class="btn" :class="filters.favorite ? 'btn-primary' : 'btn-secondary'" :aria-pressed="filters.favorite" @click="filters.favorite = !filters.favorite">
          <Icon :name="filters.favorite ? 'starFill' : 'star'" :size="16" /> 仅看收藏
        </button>
      </div>

      <div class="filter-row mt-3">
        <span class="filter-label">方向</span>
        <div class="row wrap gap-2">
          <button class="chip" :class="{ active: !filters.category }" @click="filters.category = ''">全部</button>
          <button v-for="c in categories" :key="c.id" class="chip" :class="{ active: filters.category === c.id }" @click="filters.category = c.id">
            {{ c.name }} <span class="count">{{ c.count }}</span>
          </button>
        </div>
      </div>

      <div class="row wrap gap-4 mt-3">
        <div class="filter-row">
          <span class="filter-label">题型</span>
          <div class="segmented" role="radiogroup" aria-label="题型">
            <button v-for="t in TYPE_OPTIONS" :key="t.id" role="radio" :aria-checked="filters.type === t.id" :class="{ active: filters.type === t.id }" @click="filters.type = t.id">{{ t.name }}</button>
          </div>
        </div>
        <div class="filter-row">
          <span class="filter-label">难度</span>
          <div class="segmented" role="radiogroup" aria-label="难度">
            <button v-for="d in DIFFICULTY_OPTIONS" :key="d.id" role="radio" :aria-checked="filters.difficulty === d.id" :class="{ active: filters.difficulty === d.id }" @click="filters.difficulty = d.id">{{ d.name }}</button>
          </div>
        </div>
      </div>

      <div v-if="tags.length" class="filter-row mt-3">
        <span class="filter-label">标签</span>
        <div class="row wrap gap-2">
          <button v-for="t in tags" :key="t.name" class="chip chip-sm" :class="{ active: filters.tag === t.name }" @click="toggleTag(t.name)">
            # {{ t.name }} <span class="count">{{ t.count }}</span>
          </button>
          <button v-if="(meta?.tags?.length || 0) > 16" class="btn btn-ghost btn-sm" @click="showAllTags = !showAllTags">
            {{ showAllTags ? '收起' : `更多 ${meta.tags.length - 16}` }}
            <Icon :name="showAllTags ? 'arrowUp' : 'chevronDown'" :size="14" />
          </button>
        </div>
      </div>
    </section>

    <div class="row mt-4 mb-2 list-head">
      <span class="text-soft text-sm">
        共 <b class="text-primary">{{ total }}</b> 道题目<template v-if="hasFilters">（已筛选）</template>
      </span>
      <button v-if="hasFilters" class="btn btn-ghost btn-sm ml-auto" @click="resetFilters"><Icon name="refresh" :size="14" /> 重置筛选</button>
    </div>

    <div v-if="error" class="alert alert-danger">
      <Icon class="alert-icon" name="alert" :size="18" />
      <div class="flex-1">{{ error }}</div>
      <button class="btn btn-sm btn-secondary" @click="loadList">重试</button>
    </div>

    <div v-else-if="loading && !items.length" class="stack gap-3">
      <div v-for="i in 5" :key="i" class="skeleton sk-card" />
    </div>

    <div v-else-if="!items.length" class="card empty">
      <div class="empty-icon"><Icon name="search" :size="28" /></div>
      <div class="empty-title">{{ filters.favorite ? '还没有收藏题目' : '没有找到匹配的题目' }}</div>
      <div class="empty-desc">{{ filters.favorite ? '浏览题库时点击星标即可收藏重点题目。' : '试试换个关键词或放宽筛选条件。' }}</div>
      <button v-if="hasFilters" class="btn btn-secondary mt-3" @click="resetFilters">清除筛选</button>
    </div>

    <TransitionGroup v-else name="fade" tag="div" class="stack gap-3 list" :class="{ dim: loading }">
      <article
        v-for="q in items"
        :key="q.id"
        class="card card-hover q-card"
        tabindex="0"
        role="button"
        :aria-label="`查看题目：${q.title}`"
        @click="openDetail(q)"
        @keydown.enter.prevent="openDetail(q)"
      >
        <div class="q-main">
          <div class="row wrap gap-2 q-tags">
            <span class="tag" :class="`tag-${TYPE_TONE[q.type]}`">{{ q.type_name }}</span>
            <span class="tag" :class="`tag-${DIFFICULTY_TONE[q.difficulty]}`">{{ q.difficulty_name }}</span>
            <span v-for="t in q.tags.slice(0, 4)" :key="t" class="tag">#{{ t }}</span>
          </div>
          <h3 class="q-title clamp-2">{{ q.title }}</h3>
          <p class="text-dim text-sm clamp-2 mt-1">考察要点：{{ q.key_points.join(' · ') }}</p>
        </div>
        <div class="q-side">
          <button
            class="btn btn-icon btn-ghost fav"
            :class="{ on: q.favorite }"
            :aria-label="q.favorite ? '取消收藏' : '收藏'"
            :aria-pressed="q.favorite"
            @click.stop="toggleFavorite(q)"
          >
            <Icon :name="q.favorite ? 'starFill' : 'star'" :size="18" />
          </button>
          <span v-if="q.practice_count" class="text-xs text-success row gap-1"><Icon name="checkCircle" :size="12" /> 练习 {{ q.practice_count }} 次</span>
          <span v-else class="text-xs text-dim">未练习</span>
        </div>
      </article>
    </TransitionGroup>

    <nav v-if="totalPages > 1" class="pager mt-4" aria-label="分页">
      <button class="btn btn-secondary btn-sm" :disabled="page <= 1" @click="page--"><Icon name="chevronLeft" :size="14" /> 上一页</button>
      <template v-for="(n, i) in pageNumbers" :key="i">
        <span v-if="n === '…'" class="text-dim">…</span>
        <button v-else class="btn btn-sm" :class="n === page ? 'btn-primary' : 'btn-ghost'" :aria-current="n === page ? 'page' : undefined" @click="page = n">{{ n }}</button>
      </template>
      <button class="btn btn-secondary btn-sm" :disabled="page >= totalPages" @click="page++">下一页 <Icon name="chevronRight" :size="14" /></button>
    </nav>

    <!-- 题目详情 -->
    <Transition name="fade">
      <div v-if="drawerOpen" class="overlay" @click="closeDetail" />
    </Transition>
    <Transition name="drawer">
      <aside v-if="drawerOpen && detail" class="drawer qd" role="dialog" aria-modal="true" aria-label="题目详情">
        <div class="drawer-head">
          <div class="row wrap gap-2">
            <span class="tag" :class="`tag-${TYPE_TONE[detail.type]}`">{{ detail.type_name }}</span>
            <span class="tag" :class="`tag-${DIFFICULTY_TONE[detail.difficulty]}`">{{ detail.difficulty_name }}</span>
          </div>
          <div class="row gap-1 ml-auto">
            <button class="btn btn-icon btn-ghost fav" :class="{ on: detail.favorite }" :aria-label="detail.favorite ? '取消收藏' : '收藏'" @click="toggleFavorite(detail)">
              <Icon :name="detail.favorite ? 'starFill' : 'star'" :size="18" />
            </button>
            <button class="btn btn-icon btn-ghost" aria-label="关闭" @click="closeDetail"><Icon name="x" :size="18" /></button>
          </div>
        </div>

        <div class="drawer-body">
          <h2 class="qd-title">{{ detail.title }}</h2>
          <div class="row wrap gap-2 mt-2">
            <span v-for="t in detail.tags" :key="t" class="tag">#{{ t }}</span>
          </div>
          <div v-if="detail.positions?.length" class="row wrap gap-2 mt-2 text-xs text-dim">
            <Icon name="briefcase" :size="12" /> 适用岗位：
            <span v-for="p in detail.positions" :key="p" class="pos-link">{{ catalog.nameOf(p) }}</span>
          </div>

          <section class="mt-4">
            <div class="section-title"><Icon name="target" :size="16" /> 考察要点</div>
            <ol class="points">
              <li v-for="(k, i) in detail.key_points" :key="i">{{ k }}</li>
            </ol>
          </section>

          <section class="mt-4">
            <div class="row">
              <div class="section-title"><Icon name="bulb" :size="16" /> 答题思路</div>
              <button class="btn btn-ghost btn-sm ml-auto" @click="showOutline = !showOutline">
                <Icon name="eye" :size="14" /> {{ showOutline ? '隐藏' : '查看' }}
              </button>
            </div>
            <div v-if="showOutline" class="outline">{{ detail.answer_outline }}</div>
            <div v-else class="outline masked" @click="showOutline = true">建议先独立作答，再展开对照答题思路</div>
          </section>

          <section class="mt-4">
            <div class="section-title"><Icon name="edit" :size="16" /> 我的作答</div>
            <textarea v-model="answer" class="textarea" rows="6" maxlength="4000" placeholder="用自己的话组织答案，建议按「结论 → 原理 → 案例 → 取舍」展开……" />
            <div class="row wrap gap-3 mt-2">
              <div class="row gap-1" role="radiogroup" aria-label="自评">
                <span class="text-xs text-dim">自评</span>
                <button
                  v-for="n in 5"
                  :key="n"
                  class="rate"
                  :class="{ on: n <= rating }"
                  role="radio"
                  :aria-checked="n === rating"
                  :aria-label="`${n} 分`"
                  @click="rating = rating === n ? 0 : n"
                >
                  <Icon :name="n <= rating ? 'starFill' : 'star'" :size="16" />
                </button>
              </div>
              <span class="text-xs text-dim ml-auto">{{ answer.length }}/4000</span>
              <button class="btn btn-primary btn-sm" :disabled="!answer.trim() || submitting" @click="submitPractice">
                <span v-if="submitting" class="spinner" /> <Icon v-else name="check" :size="14" /> 保存练习
              </button>
            </div>
          </section>

          <section class="mt-4">
            <div class="section-title"><Icon name="history" :size="16" /> 练习记录 <span class="text-dim text-xs">{{ detail.practices?.length || 0 }}</span></div>
            <div v-if="detailLoading" class="skeleton sk-line" />
            <div v-else-if="!detail.practices?.length" class="text-dim text-sm">还没有练习记录</div>
            <div v-else class="stack gap-2">
              <div v-for="p in detail.practices" :key="p.practice_id" class="practice">
                <div class="row text-xs text-dim">
                  <Icon name="clock" :size="12" /> {{ formatTime(p.created_at) }}
                  <span v-if="p.self_rating" class="ml-auto stars">
                    <Icon v-for="n in p.self_rating" :key="n" name="starFill" :size="12" />
                  </span>
                </div>
                <p class="text-sm mt-1 practice-text">{{ p.answer }}</p>
              </div>
            </div>
          </section>
        </div>

        <div class="drawer-foot">
          <button class="btn btn-gradient btn-block" @click="practiceInterview(detail)">
            <Icon name="play" :size="16" /> 用此题开始模拟面试
          </button>
        </div>
      </aside>
    </Transition>

    <!-- 随机抽题 -->
    <Transition name="fade">
      <div v-if="randomOpen" class="overlay center" @click.self="randomOpen = false">
        <div class="modal rand" role="dialog" aria-modal="true" aria-label="随机抽题">
          <div class="row mb-4">
            <div>
              <div class="section-title"><Icon name="shuffle" :size="16" /> 随机抽题</div>
              <p class="text-xs text-dim">按当前岗位 / 题型 / 难度筛选随机抽取 5 题</p>
            </div>
            <button class="btn btn-icon btn-ghost ml-auto" aria-label="关闭" @click="randomOpen = false"><Icon name="x" :size="18" /></button>
          </div>
          <div v-if="randomLoading" class="stack gap-2">
            <div v-for="i in 5" :key="i" class="skeleton sk-line" />
          </div>
          <div v-else-if="!randomItems.length" class="empty">
            <div class="empty-title">当前条件下没有题目</div>
          </div>
          <div v-else class="stack gap-2">
            <button v-for="(q, i) in randomItems" :key="q.id" class="rand-item" @click="openFromRandom(q)">
              <span class="rand-idx">{{ i + 1 }}</span>
              <span class="flex-1 text-left">
                <span class="clamp-2">{{ q.title }}</span>
                <span class="row gap-2 mt-1">
                  <span class="tag" :class="`tag-${TYPE_TONE[q.type]}`">{{ q.type_name }}</span>
                  <span class="tag" :class="`tag-${DIFFICULTY_TONE[q.difficulty]}`">{{ q.difficulty_name }}</span>
                </span>
              </span>
              <Icon name="chevronRight" :size="16" class="text-dim" />
            </button>
          </div>
          <div class="row mt-4">
            <button class="btn btn-secondary ml-auto" :disabled="randomLoading" @click="drawRandom"><Icon name="refresh" :size="14" /> 换一批</button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.qb { padding-bottom: 48px; }
.stats { margin-top: 8px; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); }
.stat-value small { font-weight: 500; }
.filters { padding: 18px 20px; }
.search { min-width: 260px; }
.pos-select { width: 200px; }
.filter-row { display: flex; align-items: flex-start; gap: 12px; }
.filter-label { flex: none; width: 36px; padding-top: 6px; font-size: 13px; color: var(--text-dim); }
.chip-sm { font-size: 12px; padding: 3px 10px; }
.list-head { align-items: center; }
.list { transition: opacity var(--dur) var(--ease); }
.list.dim { opacity: .55; pointer-events: none; }
.sk-card { height: 104px; border-radius: var(--radius); }
.sk-line { height: 56px; border-radius: var(--radius-sm); }

.q-card { display: flex; gap: 16px; padding: 16px 18px; cursor: pointer; outline: none; }
.q-card:focus-visible { box-shadow: 0 0 0 2px var(--primary-border); }
.q-main { flex: 1; min-width: 0; }
.q-title { margin: 8px 0 0; font-size: 15px; font-weight: 600; line-height: 1.55; color: var(--text); }
.q-side { flex: none; display: flex; flex-direction: column; align-items: flex-end; justify-content: space-between; gap: 8px; }
.fav { color: var(--text-dim); }
.fav.on { color: var(--warning); }

.pager { display: flex; align-items: center; justify-content: center; gap: 6px; flex-wrap: wrap; }

.qd { width: min(560px, 100vw); }
.qd-title { margin: 0; font-size: 18px; line-height: 1.6; font-weight: 650; }
.pos-link { color: var(--primary-soft); }
.points { margin: 8px 0 0; padding-left: 20px; display: grid; gap: 6px; color: var(--text-soft); line-height: 1.65; }
.outline { margin-top: 8px; padding: 12px 14px; border-radius: var(--radius-sm); background: var(--primary-bg); border: 1px solid var(--primary-border); line-height: 1.75; white-space: pre-wrap; }
.outline.masked { background: var(--bg-soft); border-style: dashed; border-color: var(--border-strong); color: var(--text-dim); text-align: center; cursor: pointer; }
.rate { background: none; border: 0; padding: 2px; color: var(--text-dim); cursor: pointer; border-radius: var(--radius-xs); }
.rate.on { color: var(--warning); }
.rate:focus-visible { outline: 2px solid var(--primary-border); }
.practice { padding: 10px 12px; border-radius: var(--radius-sm); background: var(--bg-soft); border: 1px solid var(--border); }
.practice-text { white-space: pre-wrap; color: var(--text-soft); line-height: 1.65; margin-bottom: 0; }
.stars { color: var(--warning); display: inline-flex; gap: 1px; }

.overlay.center { display: flex; align-items: center; justify-content: center; padding: 16px; }
.rand { width: min(560px, 100%); }
.rand-item { display: flex; align-items: center; gap: 12px; width: 100%; padding: 12px 14px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg-card); color: var(--text); font: inherit; text-align: left; cursor: pointer; transition: border-color var(--dur) var(--ease), background var(--dur) var(--ease); }
.rand-item:hover { border-color: var(--primary-border); background: var(--bg-hover); }
.rand-idx { flex: none; width: 26px; height: 26px; border-radius: 50%; display: grid; place-items: center; background: var(--primary-bg); color: var(--primary-soft); font-weight: 600; font-size: 13px; }
.text-left { text-align: left; }

@media (max-width: 768px) {
  .pos-select { width: 100%; }
  .search { min-width: 100%; }
  .filter-row { flex-direction: column; gap: 6px; }
  .filter-label { padding-top: 0; }
  .q-card { flex-direction: column; }
  .q-side { flex-direction: row; align-items: center; }
}
</style>
