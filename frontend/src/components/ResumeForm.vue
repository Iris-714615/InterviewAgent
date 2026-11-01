<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'

const props = defineProps({ modelValue: { type: Object, required: true } })
const p = props.modelValue

const skillsText = computed({
  get: () => (p.skills || []).join('、'),
  set: (v) => {
    p.skills = v.split(/[,，、\n;；]+/).map((s) => s.trim()).filter(Boolean)
  },
})
const awardsText = computed({
  get: () => (p.awards || []).join('\n'),
  set: (v) => {
    p.awards = v.split('\n').map((s) => s.trim()).filter(Boolean)
  },
})

const blank = {
  experiences: () => ({ company: '', role: '', period: '', tech: '', situation: '', task: '', action: '', result: '' }),
  projects: () => ({ name: '', role: '', period: '', tech: '', situation: '', task: '', action: '', result: '' }),
  education: () => ({ school: '', degree: '', major: '', period: '', note: '' }),
}
function add(key) {
  if (!p[key]) p[key] = []
  p[key].push(blank[key]())
}
function remove(key, i) {
  p[key].splice(i, 1)
}
const star = [
  { k: 'situation', label: 'S 背景', ph: '当时的业务背景/面临的问题' },
  { k: 'task', label: 'T 任务', ph: '你负责的目标与职责' },
  { k: 'action', label: 'A 行动', ph: '你采取的关键动作与技术方案' },
  { k: 'result', label: 'R 结果', ph: '可量化成果,如性能提升 40%、节省 20 人日' },
]
</script>

<template>
  <div class="rf">
    <section class="rf-sec">
      <h3 class="rf-h"><Icon name="user" :size="16" />基本信息</h3>
      <div class="rf-grid">
        <input v-model="p.name" class="textarea rf-in" placeholder="姓名" />
        <input v-model="p.title" class="textarea rf-in" placeholder="求职意向,如 前端工程师" />
        <input v-model="p.phone" class="textarea rf-in" placeholder="手机" />
        <input v-model="p.email" class="textarea rf-in" placeholder="邮箱" />
        <input v-model="p.city" class="textarea rf-in" placeholder="所在城市" />
      </div>
      <textarea v-model="p.summary" class="textarea" rows="3" placeholder="个人简介(可留空,生成时将结合 JD 自动润色)"></textarea>
    </section>

    <section class="rf-sec">
      <h3 class="rf-h"><Icon name="zap" :size="16" />专业技能</h3>
      <textarea v-model="skillsText" class="textarea" rows="2" placeholder="用顿号或逗号分隔,如 Vue3、TypeScript、Node.js"></textarea>
    </section>

    <section v-for="grp in [{ key: 'experiences', label: '工作/实习经历', icon: 'briefcase', a: 'company', b: 'role', an: '公司', bn: '职位' }, { key: 'projects', label: '项目经历', icon: 'layers', a: 'name', b: 'role', an: '项目名称', bn: '担任角色' }]" :key="grp.key" class="rf-sec">
      <div class="rf-head">
        <h3 class="rf-h"><Icon :name="grp.icon" :size="16" />{{ grp.label }}</h3>
        <button type="button" class="btn btn-ghost btn-sm" @click="add(grp.key)"><Icon name="plus" :size="14" />添加</button>
      </div>
      <div v-for="(it, i) in p[grp.key]" :key="i" class="rf-item">
        <div class="rf-grid">
          <input v-model="it[grp.a]" class="textarea rf-in" :placeholder="grp.an" />
          <input v-model="it[grp.b]" class="textarea rf-in" :placeholder="grp.bn" />
          <input v-model="it.period" class="textarea rf-in" placeholder="时间,如 2022.03 - 2024.06" />
          <input v-model="it.tech" class="textarea rf-in" placeholder="技术栈/工具" />
        </div>
        <div v-for="s in star" :key="s.k" class="rf-star">
          <span class="rf-star-k">{{ s.label }}</span>
          <textarea v-model="it[s.k]" class="textarea" rows="2" :placeholder="s.ph"></textarea>
        </div>
        <button type="button" class="btn btn-ghost btn-sm rf-del" @click="remove(grp.key, i)"><Icon name="trash" :size="14" />删除</button>
      </div>
      <p v-if="!p[grp.key] || !p[grp.key].length" class="rf-empty">暂无内容,点击右上角添加。按 STAR 填写,生成的要点更有说服力。</p>
    </section>

    <section class="rf-sec">
      <div class="rf-head">
        <h3 class="rf-h"><Icon name="graduation" :size="16" />教育经历</h3>
        <button type="button" class="btn btn-ghost btn-sm" @click="add('education')"><Icon name="plus" :size="14" />添加</button>
      </div>
      <div v-for="(it, i) in p.education" :key="i" class="rf-item">
        <div class="rf-grid">
          <input v-model="it.school" class="textarea rf-in" placeholder="学校" />
          <input v-model="it.degree" class="textarea rf-in" placeholder="学历" />
          <input v-model="it.major" class="textarea rf-in" placeholder="专业" />
          <input v-model="it.period" class="textarea rf-in" placeholder="时间" />
        </div>
        <input v-model="it.note" class="textarea rf-in" placeholder="补充,如 GPA、荣誉、主修课程" />
        <button type="button" class="btn btn-ghost btn-sm rf-del" @click="remove('education', i)"><Icon name="trash" :size="14" />删除</button>
      </div>
    </section>

    <section class="rf-sec">
      <h3 class="rf-h"><Icon name="award" :size="16" />荣誉奖项</h3>
      <textarea v-model="awardsText" class="textarea" rows="2" placeholder="每行一条"></textarea>
    </section>
  </div>
</template>

<style scoped>
.rf { display: flex; flex-direction: column; gap: 16px; }
.rf-sec { display: flex; flex-direction: column; gap: 10px; }
.rf-head { display: flex; align-items: center; justify-content: space-between; }
.rf-h { display: flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 600; color: var(--text); margin: 0; }
.rf-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.rf-in { min-height: 0; height: 38px; padding: 0 12px; resize: none; }
.rf-item { display: flex; flex-direction: column; gap: 8px; padding: 12px; border: 1px solid var(--border); border-radius: var(--radius); background: var(--bg-soft); }
.rf-star { display: grid; grid-template-columns: 56px 1fr; gap: 8px; align-items: start; }
.rf-star-k { font-size: 12px; font-weight: 600; color: var(--primary); padding-top: 8px; }
.rf-del { align-self: flex-end; color: var(--danger); }
.rf-empty { font-size: 12px; color: var(--text-dim); margin: 0; }
@media (max-width: 640px) {
  .rf-grid { grid-template-columns: 1fr; }
  .rf-star { grid-template-columns: 1fr; }
  .rf-star-k { padding-top: 0; }
}
</style>
