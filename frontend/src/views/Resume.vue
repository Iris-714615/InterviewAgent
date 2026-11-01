<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from '../components/Icon.vue'
import ResumeForm from '../components/ResumeForm.vue'
import JdInsight from '../components/JdInsight.vue'
import ResumeAnalysis from '../components/ResumeAnalysis.vue'
import { useAuthStore } from '../stores/auth'
import {
  analyzeJD, generateResume, matchResume, diagnoseResume, rewriteStar,
  coverLetter, interviewQuestions, saveResume, getSavedResume,
} from '../api'
import { toast } from '../utils/toast'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const TEMPLATES = [
  { id: 'modern', name: '现代' },
  { id: 'classic', name: '经典' },
  { id: 'minimal', name: '极简' },
  { id: 'tech', name: '技术' },
]

const blankExp = () => ({ company: '', role: '', period: '', tech: '', situation: '', task: '', action: '', result: '' })
const blankEdu = () => ({ school: '', degree: '', major: '', period: '', note: '' })

const profile = reactive({
  name: '', title: '', phone: '', email: '', city: '', summary: '',
  skills: [], experiences: [blankExp()], projects: [], education: [blankEdu()], awards: [],
})
const jdText = ref('')
const template = ref('modern')
const useAi = ref(true)
const step = ref('edit')
const jd = ref(null)
const resume = ref(null)
const analysis = reactive({ match: null, diagnose: null })
const busy = reactive({ jd: false, gen: false, save: false, extra: false })
const extra = reactive({ kind: '', text: '', questions: [] })
const starInput = ref('')
const starOut = ref(null)

const hasResume = computed(() => !!resume.value)

async function runJd() {
  if (!jdText.value.trim()) return toast.info('请先粘贴岗位 JD')
  busy.jd = true
  try {
    jd.value = await analyzeJD(jdText.value)
  } catch (e) {
    toast.error(e.message || '解析失败')
  } finally {
    busy.jd = false
  }
}

async function generate() {
  if (!profile.name.trim()) return toast.info('请至少填写姓名')
  busy.gen = true
  try {
    const res = await generateResume(JSON.parse(JSON.stringify(profile)), jdText.value, template.value, useAi.value)
    resume.value = res.resume
    jd.value = res.jd || jd.value
    step.value = 'preview'
    toast.success(res.ai ? 'AI 已生成简历' : '已生成简历(本地规则)')
    await analyze()
  } catch (e) {
    toast.error(e.message || '生成失败')
  } finally {
    busy.gen = false
  }
}

async function analyze() {
  if (!resume.value) return
  try {
    const [m, d] = await Promise.all([
      matchResume(resume.value, jdText.value),
      diagnoseResume(resume.value, jdText.value),
    ])
    analysis.match = m
    analysis.diagnose = d
  } catch (e) {
    toast.error(e.message || '分析失败')
  }
}

async function runStar() {
  if (!starInput.value.trim()) return toast.info('请输入一段经历描述')
  busy.extra = true
  try {
    starOut.value = await rewriteStar(starInput.value, jdText.value, useAi.value)
  } catch (e) {
    toast.error(e.message || '改写失败')
  } finally {
    busy.extra = false
  }
}

async function runExtra(kind) {
  if (!resume.value) return
  busy.extra = true
  extra.kind = kind
  try {
    if (kind === 'cover') {
      const r = await coverLetter(resume.value, jdText.value, useAi.value)
      extra.text = r.text || ''
    } else {
      const r = await interviewQuestions(resume.value, jdText.value, useAi.value)
      extra.questions = r.questions || []
    }
  } catch (e) {
    toast.error(e.message || '生成失败')
  } finally {
    busy.extra = false
  }
}

async function save() {
  if (!auth.isLoggedIn) {
    toast.info('登录后即可保存简历')
    return router.push({ path: '/login', query: { redirect: '/resume' } })
  }
  busy.save = true
  try {
    const title = `${resume.value.name || '简历'} · ${jd.value?.role || resume.value.title || '通用'}`
    await saveResume({ title, jd_text: jdText.value, template: template.value, resume: resume.value })
    toast.success('已保存到账号')
  } catch (e) {
    toast.error(e.message || '保存失败')
  } finally {
    busy.save = false
  }
}

async function loadSaved(id) {
  try {
    const { item } = await getSavedResume(id)
    resume.value = item.resume
    jdText.value = item.jd_text || ''
    template.value = item.template || 'modern'
    step.value = 'preview'
    if (jdText.value) runJd()
    analyze()
  } catch (e) {
    toast.error(e.message || '载入失败')
  }
}

function copyText(t) {
  navigator.clipboard?.writeText(t).then(() => toast.success('已复制'), () => toast.error('复制失败'))
}

onMounted(() => {
  if (route.query.load) loadSaved(route.query.load)
})
const printPage = () => window.print()
</script>

<template>
  <div class="resume-page">
    <header class="page-head">
      <div>
        <h1 class="page-title">AI 简历工坊</h1>
        <p class="page-sub">粘贴 JD,填写经历,一键生成匹配岗位、符合 STAR 法则的简历</p>
      </div>
      <div class="seg">
        <button :class="{ on: step === 'edit' }" @click="step = 'edit'">编辑</button>
        <button :class="{ on: step === 'preview' }" :disabled="!hasResume" @click="step = 'preview'">预览与分析</button>
      </div>
    </header>

    <div v-show="step === 'edit'" class="edit-grid">
      <section class="card pane">
        <div class="pane-head">
          <h3><Icon name="target" :size="16" /> 目标岗位 JD</h3>
          <button class="btn btn-secondary btn-sm" :disabled="busy.jd" @click="runJd">
            <span v-if="busy.jd" class="spinner" />
            <Icon v-else name="sparkles" :size="14" /> 解析 JD
          </button>
        </div>
        <textarea v-model="jdText" class="textarea" rows="8" placeholder="粘贴岗位描述,系统将提取关键技能与关键词并定向优化简历" />
        <JdInsight :data="jd" />
      </section>

      <section class="card pane">
        <div class="pane-head"><h3><Icon name="user" :size="16" /> 个人信息与经历</h3></div>
        <ResumeForm :model-value="profile" />
      </section>
    </div>

    <div v-show="step === 'edit'" class="gen-bar card">
      <div class="tpls">
        <button v-for="t in TEMPLATES" :key="t.id" class="tpl" :class="{ on: template === t.id }" @click="template = t.id">{{ t.name }}</button>
      </div>
      <label class="ai-switch"><input v-model="useAi" type="checkbox" /> 使用 AI 润色</label>
      <button class="btn btn-primary btn-lg" :disabled="busy.gen" @click="generate">
        <span v-if="busy.gen" class="spinner" />
        <Icon v-else name="zap" :size="16" /> 生成简历
      </button>
    </div>

    <div v-if="step === 'preview' && resume" class="preview-grid">
      <article class="paper" :class="'tpl-' + (resume.template || template)">
        <h2>{{ resume.name }}</h2>
        <div class="paper-title">{{ resume.title }}</div>
        <div class="paper-contact">
          <span v-if="resume.contact?.phone">{{ resume.contact.phone }}</span>
          <span v-if="resume.contact?.email">{{ resume.contact.email }}</span>
          <span v-if="resume.contact?.city">{{ resume.contact.city }}</span>
        </div>
        <section v-if="resume.summary"><h4>个人简介</h4><p>{{ resume.summary }}</p></section>
        <section v-if="resume.skills?.length">
          <h4>专业技能</h4>
          <p v-for="g in resume.skills" :key="g.group"><b>{{ g.group }}:</b>{{ (g.items || []).join('、') }}</p>
        </section>
        <section v-if="resume.experiences?.length">
          <h4>工作经历</h4>
          <div v-for="(e, i) in resume.experiences" :key="i" class="entry">
            <div class="entry-head"><b>{{ e.company || e.name }}</b><span>{{ e.role }}</span><em>{{ e.period }}</em></div>
            <div v-if="e.tech" class="entry-tech">技术栈:{{ e.tech }}</div>
            <ul><li v-for="(b, j) in e.bullets" :key="j">{{ b }}</li></ul>
          </div>
        </section>
        <section v-if="resume.projects?.length">
          <h4>项目经历</h4>
          <div v-for="(e, i) in resume.projects" :key="i" class="entry">
            <div class="entry-head"><b>{{ e.name || e.company }}</b><span>{{ e.role }}</span><em>{{ e.period }}</em></div>
            <div v-if="e.tech" class="entry-tech">技术栈:{{ e.tech }}</div>
            <ul><li v-for="(b, j) in e.bullets" :key="j">{{ b }}</li></ul>
          </div>
        </section>
        <section v-if="resume.education?.length">
          <h4>教育背景</h4>
          <div v-for="(e, i) in resume.education" :key="i" class="entry-head">
            <b>{{ e.school }}</b><span>{{ [e.degree, e.major].filter(Boolean).join(' · ') }}</span><em>{{ e.period }}</em>
          </div>
        </section>
        <section v-if="resume.awards?.length">
          <h4>荣誉奖项</h4>
          <ul><li v-for="(a, i) in resume.awards" :key="i">{{ a }}</li></ul>
        </section>
      </article>

      <aside class="side">
        <div class="card pane act-bar">
          <button class="btn btn-primary btn-sm" :disabled="busy.save" @click="save"><Icon name="download" :size="14" /> 保存</button>
          <button class="btn btn-secondary btn-sm" @click="printPage"><Icon name="file" :size="14" /> 打印/导出</button>
          <button class="btn btn-ghost btn-sm" @click="step = 'edit'"><Icon name="edit" :size="14" /> 继续编辑</button>
        </div>
        <div class="card pane"><ResumeAnalysis :match="analysis.match" :diagnose="analysis.diagnose" /></div>

        <div class="card pane">
          <div class="pane-head"><h3><Icon name="bulb" :size="16" /> STAR 改写</h3></div>
          <textarea v-model="starInput" class="textarea" rows="3" placeholder="粘贴一段经历描述,改写为 STAR 要点" />
          <button class="btn btn-secondary btn-sm mt" :disabled="busy.extra" @click="runStar">改写</button>
          <ul v-if="starOut" class="plain">
            <li v-for="(b, i) in starOut.bullets" :key="i">{{ b }}</li>
            <li v-for="(t, i) in starOut.tips" :key="'t' + i" class="dim">{{ t }}</li>
          </ul>
        </div>

        <div class="card pane">
          <div class="pane-head"><h3><Icon name="mail" :size="16" /> 求职拓展</h3></div>
          <div class="row gap-1">
            <button class="btn btn-secondary btn-sm" :disabled="busy.extra" @click="runExtra('cover')">求职信</button>
            <button class="btn btn-secondary btn-sm" :disabled="busy.extra" @click="runExtra('q')">预测面试题</button>
          </div>
          <div v-if="busy.extra" class="mt"><span class="spinner" /></div>
          <template v-else>
            <div v-if="extra.kind === 'cover' && extra.text" class="mt">
              <pre class="cover">{{ extra.text }}</pre>
              <button class="btn btn-ghost btn-sm" @click="copyText(extra.text)"><Icon name="copy" :size="14" /> 复制</button>
            </div>
            <ul v-if="extra.kind === 'q' && extra.questions.length" class="plain mt">
              <li v-for="(q, i) in extra.questions" :key="i"><span class="tag tag-info">{{ q.type }}</span> {{ q.question }}</li>
            </ul>
          </template>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.resume-page { display: flex; flex-direction: column; gap: 16px; }
.page-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.page-title { font-size: 22px; font-weight: 700; color: var(--text); margin: 0; }
.page-sub { margin: 4px 0 0; color: var(--text-soft); font-size: 13px; }
.seg { display: inline-flex; background: var(--bg-soft); border: 1px solid var(--border); border-radius: var(--radius-pill); padding: 3px; }
.seg button { border: 0; background: transparent; color: var(--text-soft); padding: 6px 14px; border-radius: var(--radius-pill); font-size: 13px; cursor: pointer; }
.seg button.on { background: var(--primary); color: var(--text-on-primary); }
.seg button:disabled { opacity: .4; cursor: not-allowed; }
.edit-grid { display: grid; grid-template-columns: 1fr 1.3fr; gap: 16px; align-items: start; }
.pane { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
.pane-head { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.pane-head h3 { margin: 0; font-size: 15px; color: var(--text); display: flex; align-items: center; gap: 6px; }
.gen-bar { display: flex; align-items: center; gap: 16px; padding: 12px 16px; flex-wrap: wrap; position: sticky; bottom: 70px; z-index: 5; background: var(--bg-glass); backdrop-filter: blur(12px); }
.tpls { display: flex; gap: 6px; flex: 1; flex-wrap: wrap; }
.tpl { border: 1px solid var(--border); background: var(--bg-card); color: var(--text-soft); padding: 6px 14px; border-radius: var(--radius-pill); font-size: 13px; cursor: pointer; }
.tpl.on { border-color: var(--primary); color: var(--primary); background: var(--primary-bg); }
.ai-switch { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text-soft); }
.preview-grid { display: grid; grid-template-columns: minmax(0, 1.5fr) minmax(280px, 1fr); gap: 16px; align-items: start; }
.side { display: flex; flex-direction: column; gap: 12px; }
.act-bar { flex-direction: row; flex-wrap: wrap; gap: 8px; }
.mt { margin-top: 8px; }
.plain { margin: 8px 0 0; padding-left: 18px; font-size: 13px; color: var(--text); display: flex; flex-direction: column; gap: 6px; }
.plain .dim { color: var(--text-dim); }
.cover { white-space: pre-wrap; font-family: var(--font); font-size: 13px; line-height: 1.7; color: var(--text); background: var(--bg-soft); padding: 12px; border-radius: var(--radius-sm); margin: 0 0 6px; }
.paper { background: #fff; color: #1f2937; border-radius: var(--radius); box-shadow: var(--shadow-card); padding: 32px 36px; font-size: 13px; line-height: 1.7; }
.paper h2 { margin: 0; font-size: 26px; }
.paper-title { color: #4f46e5; font-weight: 600; margin-top: 2px; }
.paper-contact { display: flex; gap: 14px; flex-wrap: wrap; color: #6b7280; margin: 6px 0 12px; font-size: 12px; }
.paper h4 { margin: 16px 0 6px; font-size: 14px; padding-bottom: 4px; border-bottom: 2px solid #4f46e5; color: #111827; }
.paper p { margin: 2px 0; }
.paper ul { margin: 4px 0 0; padding-left: 18px; }
.entry { margin-bottom: 10px; }
.entry-head { display: flex; gap: 10px; align-items: baseline; flex-wrap: wrap; }
.entry-head em { margin-left: auto; color: #6b7280; font-style: normal; font-size: 12px; }
.entry-tech { color: #6b7280; font-size: 12px; }
.tpl-classic h4 { border-bottom: 1px solid #111827; }
.tpl-classic .paper-title { color: #111827; }
.tpl-minimal h4 { border: 0; text-transform: none; color: #4f46e5; }
.tpl-minimal .paper-title { color: #6b7280; }
.tpl-tech { background: #0f172a; color: #e2e8f0; }
.tpl-tech h4 { color: #38bdf8; border-color: #38bdf8; }
.tpl-tech .paper-title { color: #38bdf8; }
.tpl-tech .paper-contact, .tpl-tech .entry-head em, .tpl-tech .entry-tech { color: #94a3b8; }
@media (max-width: 900px) {
  .edit-grid, .preview-grid { grid-template-columns: 1fr; }
  .paper { padding: 20px 18px; }
  .gen-bar { bottom: 64px; }
}
@media print {
  .page-head, .side, .gen-bar { display: none !important; }
  .preview-grid { display: block; }
  .paper { box-shadow: none; padding: 0; }
}
</style>
