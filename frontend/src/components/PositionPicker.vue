<template>
  <div class="picker">
    <!-- 第一步：岗位 -->
    <section class="step">
      <header class="step-head">
        <span class="step-no">1</span>
        <div>
          <h3 class="step-title">选择目标岗位</h3>
          <p class="step-desc">覆盖 {{ catalog.positions.length || '40+' }} 个热门岗位，也可以输入任意自定义岗位</p>
        </div>
      </header>

      <div class="toolbar">
        <div class="input-group search">
          <Icon name="search" :size="16" class="icon-lead" />
          <input v-model.trim="keyword" class="input" placeholder="搜索岗位、技能关键词，如 Java、增长、算法" aria-label="搜索岗位" />
        </div>
        <div class="segmented" role="tablist" aria-label="岗位来源">
          <button type="button" :class="{ active: !customMode }" @click="customMode = false">岗位库</button>
          <button type="button" :class="{ active: customMode }" @click="enterCustom">自定义岗位</button>
        </div>
      </div>

      <template v-if="!customMode">
        <div class="chips" role="tablist" aria-label="岗位分类">
          <button type="button" class="chip" :class="{ active: !category }" @click="category = ''">
            <Icon name="grid" :size="14" /> 全部 <span class="count">{{ catalog.positions.length }}</span>
          </button>
          <button
            v-for="c in catalog.categories"
            :key="c.id"
            type="button"
            class="chip"
            :class="{ active: category === c.id }"
            @click="category = c.id"
          >
            <Icon :name="c.icon" :size="14" /> {{ c.name }} <span class="count">{{ c.count }}</span>
          </button>
        </div>

        <div v-if="catalog.loading && !catalog.loaded" class="pos-grid">
          <div v-for="i in 8" :key="i" class="skeleton pos-skeleton" />
        </div>
        <div v-else-if="catalog.error" class="alert alert-warning">
          <Icon name="alert" :size="16" /> {{ catalog.error }}
          <button type="button" class="btn btn-sm btn-ghost ml-auto" @click="catalog.load(true)">重试</button>
        </div>
        <div v-else-if="!filtered.length" class="empty compact">
          <div class="empty-icon"><Icon name="search" :size="22" /></div>
          <div class="empty-title">没有找到“{{ keyword }}”</div>
          <div class="empty-desc">可以直接把它作为自定义岗位开始面试</div>
          <button type="button" class="btn btn-sm btn-primary mt-3" @click="useKeywordAsCustom">
            <Icon name="plus" :size="14" /> 以“{{ keyword }}”作为岗位
          </button>
        </div>
        <div v-else class="pos-grid" role="listbox" aria-label="岗位列表">
          <button
            v-for="p in filtered"
            :key="p.id"
            type="button"
            role="option"
            class="pos-card"
            :class="{ active: direction === p.id }"
            :aria-selected="direction === p.id"
            @click="select(p.id)"
          >
            <div class="pos-top">
              <span class="pos-name">{{ p.name }}</span>
              <span v-if="p.hot" class="tag tag-warning hot"><Icon name="zap" :size="11" />热门</span>
              <Icon v-if="direction === p.id" name="checkCircle" :size="18" class="pos-check" />
            </div>
            <p class="pos-focus clamp-2">{{ p.focus }}</p>
            <div class="pos-skills">
              <span v-for="s in (p.skills || []).slice(0, 4)" :key="s" class="skill">{{ s }}</span>
            </div>
          </button>
        </div>
      </template>

      <div v-else class="custom">
        <label class="field">
          <span class="field-label">岗位名称</span>
          <div class="input-group">
            <Icon name="briefcase" :size="16" class="icon-lead" />
            <input
              ref="customInput"
              v-model="customName"
              class="input"
              maxlength="40"
              placeholder="例如：自动驾驶感知算法工程师、跨境电商运营"
              @input="applyCustom"
            />
          </div>
          <span class="field-hint">AI 面试官会根据岗位名称与下方 JD 动态生成问题</span>
        </label>
        <div class="wrap gap-2 mt-3">
          <span class="text-xs text-dim">试试：</span>
          <button v-for="s in customSuggestions" :key="s" type="button" class="chip chip-sm" @click="pickCustom(s)">{{ s }}</button>
        </div>
      </div>
    </section>

    <!-- 第二步：面试类型 -->
    <section class="step">
      <header class="step-head">
        <span class="step-no">2</span>
        <div>
          <h3 class="step-title">选择面试轮次</h3>
          <p class="step-desc">不同轮次的面试官风格与考察重点不同</p>
        </div>
      </header>
      <div class="role-grid" role="radiogroup" aria-label="面试类型">
        <button
          v-for="r in ROLE_OPTIONS"
          :key="r.id"
          type="button"
          role="radio"
          class="role-card"
          :class="{ active: role === r.id }"
          :aria-checked="role === r.id"
          @click="$emit('update:role', r.id)"
        >
          <span class="role-icon"><Icon :name="r.icon" :size="18" /></span>
          <span class="role-text">
            <span class="role-name">{{ r.name }}</span>
            <span class="role-desc">{{ r.desc }}</span>
          </span>
        </button>
      </div>
    </section>

    <!-- 第三步：JD -->
    <section class="step">
      <header class="step-head">
        <span class="step-no">3</span>
        <div>
          <h3 class="step-title">岗位描述 <span class="text-dim text-sm">（可选）</span></h3>
          <p class="step-desc">粘贴 JD 或写下目标公司、级别，问题会更贴近真实面试</p>
        </div>
      </header>
      <label class="field">
        <textarea
          :value="positionDescription"
          class="textarea"
          rows="4"
          :maxlength="MAX_DESC"
          placeholder="例如：字节跳动 · 高级后端工程师，负责高并发交易链路，要求熟悉 Go、Kafka、分布式事务……"
          @input="$emit('update:positionDescription', $event.target.value)"
        />
        <span class="field-hint row">
          <span>内容仅用于本场面试出题</span>
          <span class="ml-auto" :class="{ 'text-warning': positionDescription.length > MAX_DESC * 0.9 }">
            {{ positionDescription.length }}/{{ MAX_DESC }}
          </span>
        </span>
      </label>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import Icon from './Icon.vue'
import { CUSTOM_PREFIX, ROLE_OPTIONS, useCatalogStore } from '../stores/catalog'

const MAX_DESC = 600

const props = defineProps({
  direction: { type: String, default: '' },
  role: { type: String, default: 'technical' },
  positionDescription: { type: String, default: '' }
})
const emit = defineEmits(['update:direction', 'update:role', 'update:positionDescription'])

const catalog = useCatalogStore()
const keyword = ref('')
const category = ref('')
const customMode = ref(props.direction.startsWith(CUSTOM_PREFIX))
const customName = ref(customMode.value ? props.direction.slice(CUSTOM_PREFIX.length) : '')
const customInput = ref(null)

const customSuggestions = ['游戏客户端工程师', '芯片验证工程师', '咨询顾问', '新媒体编辑', '投资分析师', '供应链经理']

const filtered = computed(() => {
  const kw = keyword.value.toLowerCase()
  return catalog.positions.filter((p) => {
    if (category.value && p.category !== category.value) return false
    if (!kw) return true
    return [p.name, p.focus, ...(p.skills || [])].some((t) => String(t).toLowerCase().includes(kw))
  })
})

function select(id) {
  emit('update:direction', id)
}

function applyCustom() {
  const name = customName.value.trim()
  emit('update:direction', name ? `${CUSTOM_PREFIX}${name}` : '')
}

function pickCustom(name) {
  customName.value = name
  applyCustom()
}

async function enterCustom() {
  customMode.value = true
  if (keyword.value && !customName.value) customName.value = keyword.value
  applyCustom()
  await nextTick()
  customInput.value?.focus()
}

function useKeywordAsCustom() {
  customName.value = keyword.value
  enterCustom()
}

// 从岗位库切回时，若当前是自定义值则清空，避免误用
watch(customMode, (custom) => {
  if (!custom && props.direction.startsWith(CUSTOM_PREFIX)) emit('update:direction', '')
})

watch(() => props.direction, (d) => {
  if (d?.startsWith(CUSTOM_PREFIX)) {
    customMode.value = true
    customName.value = d.slice(CUSTOM_PREFIX.length)
  }
})

onMounted(() => catalog.load())
</script>

<style scoped>
.picker { display: flex; flex-direction: column; gap: 28px; }
.step { display: flex; flex-direction: column; gap: 14px; }
.step-head { display: flex; gap: 12px; align-items: flex-start; }
.step-no {
  flex: none; width: 26px; height: 26px; border-radius: 50%;
  display: grid; place-items: center; font-size: 13px; font-weight: 700;
  background: var(--primary-bg); color: var(--primary); border: 1px solid var(--primary-border);
}
.step-title { margin: 0; font-size: 15px; font-weight: 650; color: var(--text); }
.step-desc { margin: 2px 0 0; font-size: 13px; color: var(--text-dim); }

.toolbar { display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.search { flex: 1; min-width: 220px; }

.chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip-sm { padding: 4px 10px; font-size: 12px; }

.pos-grid {
  display: grid; gap: 10px;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  max-height: 420px; overflow-y: auto; padding: 2px; margin: -2px;
}
.pos-skeleton { height: 112px; border-radius: var(--radius); }
.pos-card {
  text-align: left; cursor: pointer; font: inherit; color: inherit;
  display: flex; flex-direction: column; gap: 8px;
  padding: 14px; border-radius: var(--radius);
  background: var(--bg-card); border: 1px solid var(--border);
  transition: border-color var(--dur) var(--ease), box-shadow var(--dur) var(--ease), transform var(--dur) var(--ease);
}
.pos-card:hover { border-color: var(--border-strong); transform: translateY(-1px); box-shadow: var(--shadow-xs); }
.pos-card:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.pos-card.active { border-color: var(--primary); background: var(--primary-bg); box-shadow: 0 0 0 3px var(--primary-glow); }
.pos-top { display: flex; align-items: center; gap: 6px; }
.pos-name { font-weight: 600; font-size: 14px; color: var(--text); }
.hot { padding: 1px 6px; font-size: 11px; gap: 2px; }
.pos-check { margin-left: auto; color: var(--primary); }
.pos-focus { margin: 0; font-size: 12.5px; line-height: 1.55; color: var(--text-soft); min-height: 38px; }
.pos-skills { display: flex; gap: 4px; flex-wrap: wrap; }
.skill {
  font-size: 11px; padding: 2px 7px; border-radius: var(--radius-xs);
  background: var(--bg-soft); color: var(--text-dim); border: 1px solid var(--border);
}

.custom { padding: 16px; border-radius: var(--radius); border: 1px dashed var(--border-strong); background: var(--bg-soft); }
.empty.compact { padding: 28px 16px; }

.role-grid { display: grid; gap: 10px; grid-template-columns: repeat(3, 1fr); }
.role-card {
  display: flex; gap: 12px; align-items: flex-start; text-align: left;
  font: inherit; color: inherit; cursor: pointer;
  padding: 14px; border-radius: var(--radius);
  background: var(--bg-card); border: 1px solid var(--border);
  transition: border-color var(--dur) var(--ease), box-shadow var(--dur) var(--ease);
}
.role-card:hover { border-color: var(--border-strong); }
.role-card:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }
.role-card.active { border-color: var(--primary); background: var(--primary-bg); box-shadow: 0 0 0 3px var(--primary-glow); }
.role-icon {
  flex: none; width: 34px; height: 34px; border-radius: var(--radius-sm);
  display: grid; place-items: center; background: var(--bg-soft); color: var(--text-soft);
}
.role-card.active .role-icon { background: var(--gradient-primary); color: var(--text-on-primary); }
.role-text { display: flex; flex-direction: column; gap: 2px; }
.role-name { font-weight: 600; font-size: 14px; }
.role-desc { font-size: 12px; color: var(--text-dim); line-height: 1.5; }

@media (max-width: 768px) {
  .role-grid { grid-template-columns: 1fr; }
  .pos-grid { grid-template-columns: 1fr 1fr; max-height: 360px; }
}
@media (max-width: 480px) {
  .pos-grid { grid-template-columns: 1fr; }
}
</style>
