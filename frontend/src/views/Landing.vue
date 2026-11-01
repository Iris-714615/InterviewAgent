<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import Icon from '../components/Icon.vue'
import { useAuthStore } from '../stores/auth'
import { rewriteStar } from '../api'

const auth = useAuthStore()
const root = ref(null)

// ---------- 主题切换 ----------
const THEME_KEY = 'interview-agent-theme'
const theme = ref(document.documentElement.dataset.theme || 'dark')
function toggleTheme() {
  const next = theme.value === 'dark' ? 'light' : 'dark'
  theme.value = next
  document.documentElement.dataset.theme = next
  try { localStorage.setItem(THEME_KEY, next) } catch (e) { /* 忽略存储失败 */ }
  const meta = document.querySelector('meta[name="theme-color"]')
  if (meta) meta.setAttribute('content', next === 'dark' ? '#000000' : '#fff8fa')
}

// ---------- 痒点：STAR 改写体验 ----------
const starInput = ref('负责公司小程序开发，提升了用户体验')
const starLoading = ref(false)
const starError = ref('')
const starResult = ref(null)
const FALLBACK = {
  bullets: [
    '主导公司微信小程序从 0 到 1 的开发与迭代，覆盖商品浏览、下单与会员中心 3 大核心模块',
    '通过分包加载与接口合并优化首屏，页面加载耗时由 3.2s 降至 1.4s，用户留存率提升 18%',
  ],
  tips: ['补充真实的业务背景与团队规模', '用具体数字量化结果，如耗时、转化率、留存', '突出你本人的决策与贡献，而非团队整体'],
  fallback: true,
}
async function runStar() {
  const text = starInput.value.trim()
  if (!text || starLoading.value) return
  starLoading.value = true
  starError.value = ''
  try {
    const res = await rewriteStar(text, '', false)
    const bullets = (res && res.bullets) || []
    if (!bullets.length) throw new Error('empty')
    starResult.value = { bullets, tips: res.tips || [], fallback: false }
  } catch (e) {
    // 接口失败时使用本地示例兜底
    starError.value = '暂时无法连接服务，下面是一份示例效果'
    starResult.value = FALLBACK
  } finally {
    starLoading.value = false
  }
}

// ---------- 静态内容数据 ----------
const navLinks = [
  { href: '#pain', label: '痛点' },
  { href: '#features', label: '功能' },
  { href: '#flow', label: '流程' },
  { href: '#faq', label: 'FAQ' },
]
const pains = [
  { icon: 'mail', title: '简历投出去没回音', solve: '按 JD 反推关键词，逐条对齐岗位要求，让 HR 一眼看到匹配点' },
  { icon: 'search', title: '看不懂 JD 在要什么', solve: '自动提炼硬技能、软技能与加分项，告诉你该写什么' },
  { icon: 'fileText', title: '项目经历写成流水账', solve: '用 STAR 法则改写，补上背景、动作与可量化的结果' },
  { icon: 'mic', title: '一面试就紧张卡壳', solve: '语音或文字模拟面试，反复练到开口不慌' },
  { icon: 'chart', title: '不知道到底被刷在哪', solve: '匹配度打分加 30+ 项诊断，问题与修改建议一次列清' },
  { icon: 'list', title: '投递多了记不住进度', solve: '求职看板按阶段管理，面试时间与跟进一目了然' },
]
const steps = [
  { n: '01', icon: 'fileText', title: '粘贴 JD', desc: '把心仪岗位的描述贴进来，系统提炼关键词与要求。' },
  { n: '02', icon: 'edit', title: '补充你的经历', desc: '随手写下做过的事，不用润色，交给 STAR 改写。' },
  { n: '03', icon: 'zap', title: '一键生成并练面试', desc: '选模板导出简历，再用 AI 面试官针对岗位模拟提问。' },
]
const stats = [
  { num: '5', unit: '套', label: 'ATS 友好模板' },
  { num: '30+', unit: '项', label: '简历诊断维度' },
  { num: '100%', unit: '', label: '全程可导出' },
]
const faqs = [
  { q: '使用需要付费吗？', a: '核心功能可免费体验，你可以先生成简历、跑一场模拟面试，再决定是否长期使用。' },
  { q: '我的简历数据安全吗？', a: '游客模式下数据仅保存在你的浏览器本地。登录后才会保存到云端，你随时可以在账号页注销并删除数据。' },
  { q: '必须登录才能用吗？', a: '不需要。无需注册即可体验全部主要功能，登录只是为了在不同设备间同步和长期保存。' },
  { q: '可以导出 PDF 吗？', a: '可以。选好模板后可直接导出或打印为 PDF，版式对 ATS 解析友好。' },
  { q: '没有配置大模型 Key 能用吗？', a: '能用。未配置时会自动切换到本地规则兜底，关键词匹配、诊断与基础改写依然可用，配置后效果更好。' },
]

// ---------- 入场动效与锚点 ----------
let io = null
function setupReveal() {
  const els = root.value ? root.value.querySelectorAll('.reveal') : []
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (reduce || !('IntersectionObserver' in window)) {
    els.forEach((el) => el.classList.add('in'))
    return
  }
  io = new IntersectionObserver((entries) => {
    entries.forEach((en) => {
      if (en.isIntersecting) {
        en.target.classList.add('in')
        io.unobserve(en.target)
      }
    })
  }, { root: root.value, threshold: 0.12, rootMargin: '0px 0px -40px 0px' })
  els.forEach((el) => io.observe(el))
}
function jump(e, href) {
  const target = root.value && root.value.querySelector(href)
  if (!target) return
  e.preventDefault()
  const reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  target.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' })
}
const ctaLabel = computed(() => (auth.isLoggedIn ? '进入工作台' : '免费开始模拟面试'))

onMounted(() => {
  try { localStorage.setItem('ia-seen-landing', '1') } catch (e) { /* 忽略 */ }
  setupReveal()
})
onBeforeUnmount(() => { if (io) io.disconnect() })
</script>

<template>
  <div class="landing" ref="root">
    <!-- 吸顶导航 -->
    <header class="nav">
      <div class="nav-inner">
        <router-link to="/" class="brand" aria-label="InterviewAgent 首页">
          <span class="brand-mark"><Icon name="logo" :size="20" /></span>
          <span class="brand-name">InterviewAgent</span>
        </router-link>
        <nav class="nav-links" aria-label="页面导航">
          <a v-for="l in navLinks" :key="l.href" :href="l.href" @click="jump($event, l.href)">{{ l.label }}</a>
        </nav>
        <div class="nav-actions">
          <button class="btn btn-ghost btn-icon" type="button" :aria-label="theme === 'dark' ? '切换到浅色主题' : '切换到深色主题'" @click="toggleTheme">
            <Icon :name="theme === 'dark' ? 'sun' : 'moon'" :size="18" />
          </button>
          <template v-if="auth.isLoggedIn">
            <router-link to="/" class="btn btn-primary btn-sm">进入工作台</router-link>
          </template>
          <template v-else>
            <router-link to="/login" class="btn btn-ghost btn-sm nav-login">登录</router-link>
            <router-link to="/register" class="btn btn-primary btn-sm">注册</router-link>
          </template>
        </div>
      </div>
    </header>

    <!-- Hero -->
    <section class="hero">
      <div class="hero-glow" aria-hidden="true"></div>
      <div class="container hero-grid">
        <div class="hero-copy reveal">
          <span class="eyebrow"><Icon name="sparkles" :size="14" /> AI 简历 × 模拟面试</span>
          <h1 class="hero-title">
            投了 100 份简历石沉大海？<br />
            粘贴 JD，<span class="text-gradient">3 分钟</span>拿到一份为它量身定制的简历
          </h1>
          <p class="hero-sub">
            自动对齐岗位关键词，用 STAR 法则改写你的经历，再陪你用语音模拟一场真实面试。不用注册，打开就能用。
          </p>
          <div class="hero-cta">
            <router-link to="/chat" class="btn btn-primary btn-lg">
              {{ ctaLabel }} <Icon name="arrowRight" :size="18" />
            </router-link>
            <router-link to="/chat" class="btn btn-secondary btn-lg">先来一场模拟面试</router-link>
          </div>
          <ul class="trust">
            <li><Icon name="checkCircle" :size="16" /> 无需注册即可体验</li>
            <li><Icon name="checkCircle" :size="16" /> 5 套 ATS 友好模板</li>
            <li><Icon name="checkCircle" :size="16" /> STAR 法则自动改写</li>
          </ul>
        </div>

        <!-- JD → 简历 示意 -->
        <div class="hero-visual reveal" aria-hidden="true">
          <div class="jd-card">
            <div class="mock-label"><Icon name="file" :size="14" /> 岗位 JD</div>
            <p class="jd-line">负责前端<mark>性能优化</mark>与工程化建设</p>
            <p class="jd-line">熟悉 <mark>Vue3</mark>、<mark>TypeScript</mark>，有<mark>小程序</mark>经验</p>
            <p class="jd-line">具备良好的<mark>跨团队协作</mark>能力</p>
            <span class="jd-skeleton"></span>
            <span class="jd-skeleton short"></span>
          </div>
          <div class="flow-arrow"><Icon name="arrowRight" :size="20" /></div>
          <div class="resume-card">
            <div class="resume-top">
              <div class="resume-id">
                <span class="resume-name"></span>
                <span class="resume-role">前端工程师</span>
              </div>
              <div class="score-ring" style="--p: 92">
                <span class="score-num">92<small>%</small></span>
              </div>
            </div>
            <div class="resume-bar w80"></div>
            <div class="resume-bar w60"></div>
            <div class="resume-bar w70"></div>
            <div class="hit-tags">
              <span class="tag tag-success">Vue3</span>
              <span class="tag tag-success">TypeScript</span>
              <span class="tag tag-success">性能优化</span>
              <span class="tag tag-warning">小程序</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- 痛点 -->
    <section id="pain" class="section">
      <div class="container">
        <div class="sec-head reveal">
          <span class="eyebrow">你是不是也这样</span>
          <h2 class="sec-title">求职路上的每个坑，我们都想过了</h2>
          <p class="sec-sub">不是你不够好，只是简历和面试没有对准岗位。</p>
        </div>
        <div class="pain-grid">
          <article v-for="(p, i) in pains" :key="p.title" class="pain-card card reveal" :style="{ '--d': i * 60 + 'ms' }">
            <span class="pain-icon"><Icon :name="p.icon" :size="22" /></span>
            <h3 class="pain-title">{{ p.title }}</h3>
            <p class="pain-solve"><Icon name="check" :size="14" /> {{ p.solve }}</p>
          </article>
        </div>
      </div>
    </section>

    <!-- 爽点：核心功能 -->
    <section id="features" class="section section-alt">
      <div class="container">
        <div class="sec-head reveal">
          <span class="eyebrow">核心能力</span>
          <h2 class="sec-title">从一份简历到一个 Offer</h2>
        </div>

        <div class="feature reveal">
          <div class="feature-copy">
            <span class="feature-no">01</span>
            <h3>JD 定制简历，STAR 自动改写</h3>
            <p>贴上岗位描述，补充你做过的事。系统把经历改写成「背景、任务、行动、结果」，并自动嵌入岗位关键词。</p>
          </div>
          <div class="feature-ui" aria-hidden="true">
            <div class="ui-before">做了小程序开发</div>
            <div class="ui-arrow"><Icon name="sparkles" :size="18" /></div>
            <div class="ui-after">主导小程序重构，首屏耗时下降 55%，留存提升 18%</div>
          </div>
        </div>

        <div class="feature reverse reveal">
          <div class="feature-copy">
            <span class="feature-no">02</span>
            <h3>ATS 匹配度与简历诊断</h3>
            <p>实时给出与岗位的匹配分，列出缺失关键词和 30+ 项格式、内容诊断，告诉你先改哪里最划算。</p>
          </div>
          <div class="feature-ui" aria-hidden="true">
            <div class="diag-row"><span>关键词覆盖</span><div class="progress"><span style="width: 88%"></span></div><b>88</b></div>
            <div class="diag-row"><span>量化成果</span><div class="progress"><span style="width: 64%"></span></div><b>64</b></div>
            <div class="diag-row"><span>格式规范</span><div class="progress"><span style="width: 95%"></span></div><b>95</b></div>
          </div>
        </div>

        <div class="feature reveal">
          <div class="feature-copy">
            <span class="feature-no">03</span>
            <h3>AI 模拟面试，多维评分</h3>
            <p>语音或文字都行。AI 按岗位提问并追问，结束后从表达、逻辑、专业度等维度打分，附上改进建议。</p>
          </div>
          <div class="feature-ui" aria-hidden="true">
            <div class="bubble q"><Icon name="bot" :size="14" /> 说说你做过最有挑战的项目？</div>
            <div class="bubble a">我负责小程序性能优化，目标是……</div>
            <div class="score-chips">
              <span class="tag tag-primary">表达 86</span>
              <span class="tag tag-info">逻辑 78</span>
              <span class="tag tag-success">专业 90</span>
            </div>
          </div>
        </div>

        <div class="feature reverse reveal">
          <div class="feature-copy">
            <span class="feature-no">04</span>
            <h3>求职看板，进度不再乱</h3>
            <p>把投递的公司按「已投递、面试中、Offer」分栏管理，面试时间、跟进事项和对应简历一起放好。</p>
          </div>
          <div class="feature-ui kanban" aria-hidden="true">
            <div class="k-col"><b>已投递</b><i></i><i></i></div>
            <div class="k-col"><b>面试中</b><i class="hot"></i></div>
            <div class="k-col"><b>Offer</b><i class="ok"></i></div>
          </div>
        </div>
      </div>
    </section>

    <!-- 痒点：STAR 改写体验 -->
    <section id="demo" class="section">
      <div class="container-narrow">
        <div class="sec-head reveal">
          <span class="eyebrow">现在就试试</span>
          <h2 class="sec-title">把一句流水账，变成面试官想看的成果</h2>
          <p class="sec-sub">写下你做过的一件事，看看 STAR 改写后的样子。</p>
        </div>
        <div class="demo card reveal">
          <label class="field-label" for="star-input">你的经历</label>
          <textarea id="star-input" v-model="starInput" class="textarea" rows="3" maxlength="300" placeholder="例如：负责公司小程序开发，提升了用户体验"></textarea>
          <div class="demo-actions">
            <button class="btn btn-primary" type="button" :disabled="starLoading || !starInput.trim()" @click="runStar">
              <span v-if="starLoading" class="spinner" aria-hidden="true"></span>
              <Icon v-else name="sparkles" :size="16" />
              {{ starLoading ? '改写中…' : '看看效果' }}
            </button>
          </div>
          <div v-if="starError" class="alert alert-danger" role="alert">
            <span class="alert-icon"><Icon name="alert" :size="16" /></span>{{ starError }}
          </div>
          <div v-if="starResult" class="demo-result" aria-live="polite">
            <div class="mock-label"><Icon name="sparkles" :size="14" /> 改写结果</div>
            <ul class="bullets">
              <li v-for="(b, i) in starResult.bullets" :key="i">{{ b }}</li>
            </ul>
            <div v-if="starResult.tips && starResult.tips.length" class="tips">
              <div class="mock-label"><Icon name="bulb" :size="14" /> 还可以这样改</div>
              <ul>
                <li v-for="(t, i) in starResult.tips" :key="i">{{ t }}</li>
              </ul>
            </div>
          </div>
        </div>
        <div class="demo-cta reveal">
          <router-link to="/chat" class="btn btn-primary btn-lg">
            开始模拟面试 <Icon name="arrowRight" :size="18" />
          </router-link>
        </div>
      </div>
    </section>

    <!-- 流程 -->
    <section id="flow" class="section section-alt">
      <div class="container">
        <div class="sec-head reveal">
          <span class="eyebrow">三步搞定</span>
          <h2 class="sec-title">从零到一份定制简历，只要三步</h2>
        </div>
        <ol class="steps">
          <li v-for="(s, i) in steps" :key="s.n" class="step card reveal" :style="{ '--d': i * 80 + 'ms' }">
            <span class="step-n">{{ s.n }}</span>
            <span class="step-icon"><Icon :name="s.icon" :size="22" /></span>
            <h3>{{ s.title }}</h3>
            <p>{{ s.desc }}</p>
          </li>
        </ol>
        <div class="stats reveal">
          <div v-for="s in stats" :key="s.label" class="stat">
            <b>{{ s.num }}<small>{{ s.unit }}</small></b>
            <span>{{ s.label }}</span>
          </div>
        </div>
      </div>
    </section>

    <!-- FAQ -->
    <section id="faq" class="section">
      <div class="container-narrow">
        <div class="sec-head reveal">
          <span class="eyebrow">常见问题</span>
          <h2 class="sec-title">你可能想问</h2>
        </div>
        <div class="faq reveal">
          <details v-for="f in faqs" :key="f.q" class="faq-item">
            <summary>{{ f.q }}<Icon name="chevronDown" :size="18" /></summary>
            <p>{{ f.a }}</p>
          </details>
        </div>
      </div>
    </section>

    <!-- 页脚 CTA -->
    <section class="final">
      <div class="container">
        <div class="final-card reveal">
          <h2>下一份简历，别再靠运气</h2>
          <p>现在就贴上一份 JD，看看它和你的距离有多近。</p>
          <div class="hero-cta center">
            <router-link :to="'/chat'" class="btn btn-lg final-btn">
              {{ ctaLabel }} <Icon name="arrowRight" :size="18" />
            </router-link>
            <router-link to="/chat" class="btn btn-lg final-ghost">先来一场模拟面试</router-link>
          </div>
        </div>
      </div>
    </section>

    <footer class="footer">
      <div class="container footer-inner">
        <span class="brand-name">InterviewAgent</span>
        <span class="footer-note">AI 简历与模拟面试助手 · 游客可免登录体验</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
.landing {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font);
  scroll-behavior: smooth;
}
.container, .container-narrow { padding: 0 clamp(16px, 4vw, 32px); }

/* 导航 */
.nav {
  position: sticky;
  top: 0;
  z-index: 50;
  background: var(--bg-glass);
  -webkit-backdrop-filter: saturate(160%) blur(16px);
  backdrop-filter: saturate(160%) blur(16px);
  border-bottom: 1px solid var(--border);
}
.nav-inner {
  max-width: 1160px;
  margin: 0 auto;
  height: 64px;
  padding: 0 clamp(16px, 4vw, 32px);
  display: flex;
  align-items: center;
  gap: 24px;
}
.nav .brand { padding: 0; gap: 10px; text-decoration: none; color: var(--text); }
.nav-links { display: flex; gap: 4px; margin-left: 12px; flex: 1; }
.nav-links a {
  padding: 8px 12px;
  border-radius: var(--radius-pill);
  color: var(--text-soft);
  font-size: 14px;
  text-decoration: none;
  transition: background var(--dur) var(--ease), color var(--dur) var(--ease);
}
.nav-links a:hover { background: var(--bg-hover); color: var(--text); }
.nav-actions { display: flex; align-items: center; gap: 8px; margin-left: auto; }

/* 滚动显现 */
.reveal {
  opacity: 0;
  transform: translateY(24px);
  transition: opacity 0.7s var(--ease) var(--d, 0ms), transform 0.7s var(--ease) var(--d, 0ms);
}
.reveal.in { opacity: 1; transform: none; }

/* Hero */
.hero { position: relative; overflow: hidden; padding: clamp(40px, 8vw, 96px) 0 clamp(48px, 8vw, 96px); }
.hero-glow {
  position: absolute;
  top: -180px;
  left: 50%;
  width: min(900px, 120vw);
  height: 560px;
  transform: translateX(-50%);
  background: radial-gradient(closest-side, var(--primary-glow), transparent 70%);
  opacity: 0.7;
  pointer-events: none;
}
.hero-grid {
  position: relative;
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: clamp(32px, 5vw, 64px);
  align-items: center;
}
.hero-copy { min-width: 0; }
.hero-title {
  margin: 16px 0 18px;
  font-size: clamp(30px, 4.6vw, 52px);
  line-height: 1.18;
  letter-spacing: -0.02em;
  font-weight: 800;
}
.hero-sub { margin: 0 0 28px; max-width: 520px; font-size: clamp(15px, 1.6vw, 17px); line-height: 1.75; color: var(--text-soft); }
.hero-cta { display: flex; flex-wrap: wrap; gap: 12px; }
.hero-cta.center { justify-content: center; }
.trust { list-style: none; margin: 24px 0 0; padding: 0; display: flex; flex-wrap: wrap; gap: 10px 20px; color: var(--text-dim); font-size: 13px; }
.trust li { display: inline-flex; align-items: center; gap: 6px; }
.trust li svg { color: var(--success); }
/* Hero 示意 */
.hero-visual { position: relative; display: flex; flex-direction: column; gap: 14px; min-width: 0; }
.jd-card, .resume-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
  padding: 18px 20px;
}
.jd-card { margin-right: 12%; }
.resume-card { margin-left: 12%; border-color: var(--primary-border); box-shadow: var(--shadow-glow); }
.mock-label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 10px;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-dim);
}
.jd-line { margin: 0 0 8px; font-size: 14px; line-height: 1.6; color: var(--text-soft); }
.jd-line mark { background: var(--primary-bg); color: var(--primary-soft); padding: 1px 6px; border-radius: var(--radius-xs); font-weight: 600; }
.jd-skeleton { display: block; height: 8px; margin-top: 10px; border-radius: var(--radius-pill); background: var(--bg-active); }
.jd-skeleton.short { width: 55%; }
.flow-arrow {
  align-self: center;
  width: 38px;
  height: 38px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: var(--primary);
  color: var(--text-on-primary);
  transform: rotate(90deg);
  box-shadow: var(--shadow-soft);
}
.resume-top { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.resume-id { display: flex; flex-direction: column; gap: 8px; }
.resume-name { display: block; width: 90px; height: 12px; border-radius: var(--radius-pill); background: var(--text); opacity: 0.85; }
.resume-role { font-size: 13px; color: var(--text-dim); }
.score-ring {
  position: relative;
  width: 68px;
  height: 68px;
  flex: none;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: conic-gradient(var(--primary) calc(var(--p) * 1%), var(--bg-active) 0);
}
.score-ring::before { content: ''; position: absolute; inset: 7px; border-radius: 50%; background: var(--bg-card); }
.score-num { position: relative; font-size: 18px; font-weight: 800; color: var(--text); }
.score-num small { font-size: 11px; font-weight: 600; color: var(--text-dim); }
.resume-bar { height: 8px; margin-bottom: 9px; border-radius: var(--radius-pill); background: var(--bg-active); }
.resume-bar.w80 { width: 80%; }
.resume-bar.w60 { width: 60%; }
.resume-bar.w70 { width: 70%; }
.hit-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 14px; }

/* 通用区块 */
.section { padding: clamp(56px, 9vw, 104px) 0; }
.section-alt { background: var(--bg-soft); border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); }
.sec-head { max-width: 680px; margin: 0 auto clamp(32px, 5vw, 56px); text-align: center; }
.sec-title { margin: 12px 0 10px; font-size: clamp(24px, 3.4vw, 36px); line-height: 1.25; letter-spacing: -0.01em; font-weight: 800; }
.sec-sub { margin: 0; color: var(--text-soft); font-size: clamp(14px, 1.5vw, 16px); line-height: 1.7; }

/* 痛点 */
.pain-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.pain-card { padding: 22px; display: flex; flex-direction: column; gap: 10px; }
.pain-icon { width: 44px; height: 44px; display: grid; place-items: center; border-radius: var(--radius); background: var(--primary-bg); color: var(--primary-soft); }
.pain-title { margin: 4px 0 0; font-size: 16px; line-height: 1.5; font-weight: 700; }
.pain-solve { margin: 0; display: flex; gap: 6px; align-items: flex-start; font-size: 14px; line-height: 1.6; color: var(--text-soft); }
.pain-solve svg { flex: none; margin-top: 4px; color: var(--success); }
/* 功能 */
.feature {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: clamp(24px, 5vw, 64px);
  align-items: center;
  padding: clamp(20px, 3vw, 36px) 0;
}
.feature.reverse .feature-copy { order: 2; }
.feature-copy { min-width: 0; }
.feature-no { font-family: var(--font-mono); font-size: 13px; font-weight: 700; color: var(--primary-soft); letter-spacing: 0.1em; }
.feature-copy h3 { margin: 8px 0 12px; font-size: clamp(20px, 2.4vw, 26px); line-height: 1.3; font-weight: 800; }
.feature-copy p { margin: 0; font-size: 15px; line-height: 1.8; color: var(--text-soft); }
.feature-ui {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 22px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card);
}
.ui-before { padding: 12px 14px; border-radius: var(--radius); background: var(--bg-active); color: var(--text-dim); font-size: 14px; text-decoration: line-through; text-decoration-color: var(--border-strong); }
.ui-arrow { align-self: center; width: 34px; height: 34px; display: grid; place-items: center; border-radius: 50%; background: var(--primary); color: var(--text-on-primary); }
.ui-after { padding: 14px; border-radius: var(--radius); background: var(--primary-bg); border: 1px solid var(--primary-border); color: var(--text); font-size: 14px; font-weight: 600; line-height: 1.6; }
.diag-row { display: grid; grid-template-columns: 76px 1fr 32px; align-items: center; gap: 12px; font-size: 13px; color: var(--text-soft); }
.diag-row b { text-align: right; color: var(--text); font-variant-numeric: tabular-nums; }
.bubble { max-width: 88%; padding: 10px 14px; border-radius: var(--radius); font-size: 14px; line-height: 1.6; }
.bubble.q { display: inline-flex; align-items: center; gap: 8px; align-self: flex-start; background: var(--bg-active); color: var(--text); border-bottom-left-radius: var(--radius-xs); }
.bubble.a { align-self: flex-end; background: var(--primary-bg); border: 1px solid var(--primary-border); color: var(--text); border-bottom-right-radius: var(--radius-xs); }
.score-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 4px; }
.feature-ui.kanban { flex-direction: row; align-items: flex-start; gap: 10px; }
.k-col { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; padding: 10px; border-radius: var(--radius); background: var(--bg-soft); }
.k-col b { font-size: 12px; color: var(--text-dim); font-weight: 600; }
.k-col i { display: block; height: 38px; border-radius: var(--radius-sm); background: var(--bg-card); border: 1px solid var(--border); }
.k-col i.hot { border-color: var(--warning); background: var(--warning-bg); }
.k-col i.ok { border-color: var(--success); background: var(--success-bg); }

/* STAR demo */
.demo { padding: clamp(18px, 3vw, 28px); display: flex; flex-direction: column; gap: 12px; }
.demo-actions { display: flex; justify-content: flex-end; }
.demo-result { padding: 16px; border-radius: var(--radius); background: var(--primary-bg); border: 1px solid var(--primary-border); animation: pop-in 0.4s var(--ease); }
@keyframes pop-in { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
.bullets { margin: 0; padding-left: 20px; display: flex; flex-direction: column; gap: 8px; font-size: 15px; line-height: 1.7; color: var(--text); }
.tips { margin-top: 14px; padding-top: 12px; border-top: 1px dashed var(--primary-border); }
.tips ul { margin: 0; padding-left: 20px; font-size: 13px; line-height: 1.7; color: var(--text-soft); }
.demo-cta { display: flex; justify-content: center; margin-top: 28px; }

/* 流程与数据 */
.steps { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.step { position: relative; padding: 24px; display: flex; flex-direction: column; gap: 10px; }
.step h3 { margin: 4px 0 0; font-size: 18px; font-weight: 700; }
.step p { margin: 0; font-size: 14px; line-height: 1.7; color: var(--text-soft); }
.step-n { position: absolute; top: 14px; right: 18px; font-family: var(--font-mono); font-size: 34px; font-weight: 800; color: var(--text-dim); opacity: 0.4; }
.step-icon { width: 44px; height: 44px; display: grid; place-items: center; border-radius: var(--radius); background: var(--primary); color: var(--text-on-primary); }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-top: clamp(28px, 4vw, 48px); padding: 24px; border: 1px solid var(--border); border-radius: var(--radius-lg); background: var(--bg-card); }
.stat { display: flex; flex-direction: column; align-items: center; gap: 4px; text-align: center; }
.stat b { font-size: clamp(24px, 3vw, 34px); font-weight: 800; color: var(--primary-soft); font-variant-numeric: tabular-nums; }
.stat b small { margin-left: 2px; font-size: 14px; font-weight: 600; color: var(--text-dim); }
.stat span { font-size: 13px; color: var(--text-dim); }

/* FAQ */
.faq { display: flex; flex-direction: column; gap: 10px; }
.faq-item { border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg-card); transition: border-color var(--dur) var(--ease); }
.faq-item[open] { border-color: var(--primary-border); }
.faq-item summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-height: 52px;
  padding: 12px 18px;
  cursor: pointer;
  list-style: none;
  font-size: 15px;
  font-weight: 600;
}
.faq-item summary::-webkit-details-marker { display: none; }
.faq-item summary svg { flex: none; color: var(--text-dim); transition: transform var(--dur) var(--ease); }
.faq-item[open] summary svg { transform: rotate(180deg); color: var(--primary-soft); }
.faq-item summary:focus-visible { outline: 2px solid var(--primary); outline-offset: -2px; border-radius: var(--radius); }
.faq-item p { margin: 0; padding: 0 18px 16px; font-size: 14px; line-height: 1.8; color: var(--text-soft); }
/* 页脚 CTA */
.final { padding: 0 0 clamp(48px, 8vw, 96px); }
.final-card {
  position: relative;
  overflow: hidden;
  padding: clamp(36px, 6vw, 72px) clamp(20px, 4vw, 48px);
  border-radius: var(--radius-lg);
  background: var(--primary);
  color: var(--text-on-primary);
  text-align: center;
  box-shadow: var(--shadow-glow);
}
.final-card h2 { margin: 0 0 10px; font-size: clamp(24px, 3.6vw, 38px); line-height: 1.25; font-weight: 800; }
.final-card p { margin: 0 0 26px; font-size: clamp(14px, 1.6vw, 17px); }
.final-btn { background: var(--text-on-primary); color: #ff9fbd; border: 1px solid transparent; font-weight: 700; }
.final-btn:hover { opacity: 0.9; }
.final-ghost { background: transparent; color: var(--text-on-primary); border: 1px solid currentColor; }
.final-ghost:hover { opacity: 0.8; }
.footer { border-top: 1px solid var(--border); padding: 24px 0; }
.footer-inner { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 8px 16px; }
.footer .brand-name { font-weight: 700; }
.footer-note { font-size: 13px; color: var(--text-dim); }

/* 平板 */
@media (max-width: 960px) {
  .hero-grid { grid-template-columns: 1fr; }
  .nav-links { display: none; }
  .pain-grid { grid-template-columns: repeat(2, 1fr); }
  .stats { grid-template-columns: repeat(2, 1fr); }
}

/* 手机 */
@media (max-width: 768px) {
  .nav-inner { height: 58px; gap: 8px; }
  .nav-login { display: none; }
  .nav-actions .btn { min-height: 44px; }
  .nav-actions .btn-icon { min-width: 44px; }
  .hero-cta .btn { width: 100%; min-height: 48px; justify-content: center; }
  .jd-card { margin-right: 0; }
  .resume-card { margin-left: 0; }
  .pain-grid, .steps { grid-template-columns: 1fr; }
  .feature { grid-template-columns: 1fr; gap: 20px; }
  .feature.reverse .feature-copy { order: 0; }
  .demo-actions .btn { width: 100%; min-height: 48px; justify-content: center; }
  .demo-cta .btn { width: 100%; min-height: 48px; justify-content: center; }
  .faq-item summary { min-height: 48px; }
  .footer-inner { flex-direction: column; align-items: flex-start; }
}

/* 减少动效 */
@media (prefers-reduced-motion: reduce) {
  .landing { scroll-behavior: auto; }
  .jd-card, .resume-card, .demo-result { animation: none; }
  .reveal { opacity: 1; transform: none; transition: none; }
}
</style>
