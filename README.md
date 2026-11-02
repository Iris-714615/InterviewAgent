# 🎯 InterviewAgent 面试私教

<p align="center">
  <strong>基于个人资料库的一对一 AI 模拟面试 + 实时辅导 + 评估反馈</strong><br>
  上传简历 → 选择方向 → 真实演练 → 雷达图评估 → 迭代提升 → 拿到高薪 Offer ✨
</p>

<p align="center">
  <a href="#-核心功能">功能</a> •
  <a href="#-技术栈">技术栈</a> •
  <a href="#-快速开始">快速开始</a> •
  <a href="#-项目结构">项目结构</a> •
  <a href="#-使用流程">使用流程</a> •
  <a href="#-license">License</a>
</p>

---

## ✨ 核心功能

| 模块 | 能力 | 说明 |
|:---:|------|------|
| 🎯 **模拟面试** | 多方向 × 多角色组合 | AI 大模型应用 / AI 应用开发 / AI 产品经理 × 技术面 / HR 面 / 行为面 |
| 📚 **个人资料库** | RAG 增强提问 | 上传 PDF / Word / Markdown 简历与面经，面试官围绕你的真实经历提问 |
| 🎓 **实时辅导** | 一键求助教练 | 卡壳时切换辅导模式，获取参考答案与答题思路（不污染面试对话） |
| 📊 **评估报告** | 雷达图多维打分 | 亮点 / 短板分析、针对性改进建议、历史得分趋势可视化 |
| 🔊 **语音交互** | 双向语音 | 语音输入（本地 faster-whisper）+ TTS 朗读回复（mimo-v2.5-tts） |
| 💾 **对话持久化** | 刷新不丢失 | 前端 localStorage + 后端 JSON 双层保障，历史记录随时回顾 |
| 📱 **移动端适配** | PWA 支持 | 响应式布局，可安装到桌面像 App 一样使用 |
| ✍️ **简历工坊** | JD 定制简历 | 粘贴 JD + 个人信息，AI 按 STAR 法则生成定制简历；JD 关键词匹配、ATS 诊断、STAR 改写、求职信、针对性面试题、多模板预览与导出 |
| 📌 **求职看板** | 投递进度管理 | 登录后跟进每个岗位的状态、面试时间与复盘，可一键带 JD 生成简历 |
| 🔐 **账号体系** | 手机号 / 邮箱注册登录 | 手机号或邮箱 + 密码，PBKDF2 加盐哈希 + 自签 token；游客可体验，登录后保存简历与看板 |
| 🗂️ **题库** | 分类刷题 | 按方向 / 难度筛选、随机抽题、收藏与作答记录 |
| 🧭 **岗位库** | 热门岗位详情 | 目标岗位可展开查看职责、要求与技能画像，一键带入面试 / 简历 |
| 🔗 **平台直达** | 求职平台联动 | 按岗位关键词一键跳转 Boss直聘 / 智联招聘 / 猎聘等平台搜索 |
| 🚀 **落地页** | 首次访问引导 | 痛点 / 爽点 / 痒点文案，引导注册或直接体验 |

> 简历相关接口在未配置 LLM key 或调用失败时，自动降级为本地规则生成，响应中带 `used_ai` 标识。

---

## 🧱 技术栈

### 后端 `backend/` （Python / FastAPI）

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| Web 框架 | [FastAPI](https://fastapi.tiangolo.com/) + uvicorn | 高性能异步 API，SSE 流式输出 |
| LLM | OpenAI 兼容接口 | **动态模型路由**：按场景复杂度自动选模型，省钱省 token |
| RAG | LangChain + ChromaDB | 向量检索增强生成，`qwen-text-embedding-v4` 向量模型 |
| TTS | mimo-v2.5-tts | 中文语音合成（默认男声"苏打"） |
| ASR | faster-whisper | 本地语音识别（免费，支持 CPU/int8 量化） |
| 存储 | SQLite（会话 / 账号 / 简历 / 求职看板） | 进程重启不丢失 |
| 测试 | pytest | 覆盖鉴权、简历、看板与服务降级 |
| 文件解析 | pypdf / python-docx | 支持 PDF / Word / Markdown 上传 |

#### 💡 动态模型路由策略

```
简单应答（你好/好的/继续…）→ deepseek-v4-flash   ← 最省
常规面试 / 辅导           → deepseek-v4-pro      ← 平衡
深度评估分析             → glm-5.2              ← 最强
```

### 前端 `frontend/` （Vue 3 / Vite）

| 组件 | 技术选型 |
|------|---------|
| 框架 | Vue 3 `<script setup>` + Vue Router 4 + Pinia |
| 构建 | Vite 5 + vite-plugin-pwa |
| UI | 粉黑强对比深 / 浅双主题（`data-theme` 切换），全自研 CSS 设计系统，骨架屏与空状态，无持续跳动动画 |
| 图表 | ECharts 5（雷达图） |
| Markdown | marked.js（面试官回复渲染） |

---

## 🚀 快速开始

### 环境要求

- **Node.js** ≥ 18（前端）
- **Python** ≥ 3.10（后端）
- 一个 **OpenAI 兼容**的 LLM API Key（[DeepSeek](https://platform.deepseek.com/) / [智谱 GLM](https://open.bigmodel.cn/) / OpenAI / Qwen 等均可）

### 1️⃣ 克隆 & 后端启动

```bash
git clone https://github.com/Iris-714615/InterviewAgent.git
cd InterviewAgent/backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env               # Linux/macOS
# copy .env.example .env           # Windows
```

编辑 `.env`，填入你的 API 配置：

```ini
# ===== LLM 网关（必填）=====
API_KEY=sk-your-api-key-here
BASE_URL=https://your-openai-compatible-gateway/v1

# ===== 模型（可选，有默认值）=====
MODEL_FLASH=deepseek-v4-flash       # 简单问答（最省）
MODEL_PRO=deepseek-v4-pro           # 常规对话（平衡）
MODEL_GLM=glm-5.2                   # 深度评估（最强）
EMBEDDING_MODEL=qwen-text-embedding-v4
TTS_MODEL=mimo-v2.5-tts
TTS_VOICE=苏打                       # 音色：冰糖/茉莉(女) 苏打/白桦(男)

# ===== 应用配置（可选）=====
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true
CORS_ORIGINS=http://localhost:5173,http://localhost:4173
```

```bash
# 启动后端（默认 http://127.0.0.1:8000）
python -m app.main
```

### 2️⃣ 前端启动

```bash
cd ../frontend

npm install
npm run dev        # 默认 http://localhost:5173
```

### 3️⃣ 开始使用

1. 打开 `http://localhost:5173`（首次访问进入落地页，可注册 / 登录或直接体验）
2. 进入「📚 资料库」上传简历 / 项目笔记（PDF / Word / MD）
3. 进入「💬 面试间」选择方向与角色，发送「开始面试」
4. 卡壳时点「🎓 实时辅导」求助教练
5. 点「结束并评估」生成雷达图报告
6. 进入「✍️ 简历工坊」粘贴 JD 生成定制简历，在「📌 求职看板」跟进投递

### 运行测试

```bash
cd backend
python -m pytest -q        # 后端测试
cd ../frontend
npm run build              # 前端构建校验
```

---

## 📂 项目结构

```
InterviewAgent/
├── backend/                          # FastAPI 后端
│   ├── app/
│   │   ├── main.py                   # 入口：FastAPI 应用 + 路由注册
│   │   ├── core/
│   │   │   ├── config.py             # 配置中心（模型路由 / 路径 / CORS）
│   │   │   ├── llm.py                # LLM 封装 + 动态模型路由器
│   │   │   ├── asr.py                # 语音识别（本地/API 双模式）
│   │   │   ├── tts.py                # 语音合成（mimo-v2.5-tts）
│   │   │   └── http_cache.py         # HTTP 缓存头
│   │   ├── catalog/
│   │   │   ├── positions.py          # 岗位库数据
│   │   │   └── questions.py          # 题库数据
│   │   ├── rag/
│   │   │   ├── loader.py             # 文件加载与切片
│   │   │   ├── vectorstore.py        # Chroma 向量库管理
│   │   │   └── retriever.py          # RAG 检索器
│   │   ├── api/v1/
│   │   │   ├── chat.py               # 流式对话（SSE）
│   │   │   ├── interview.py          # 会话 CRUD
│   │   │   ├── evaluation.py         # 评估接口
│   │   │   ├── knowledge.py          # 资料库管理
│   │   │   ├── tts.py                # TTS 接口
│   │   │   ├── asr.py                # ASR 接口
│   │   │   ├── auth.py               # 注册 / 登录 / 账号
│   │   │   ├── resume.py             # 简历工坊（JD 分析 / 生成 / 诊断 / 改写 / 求职信）
│   │   │   ├── jobs.py               # 求职看板
│   │   │   ├── positions.py          # 岗位库
│   │   │   └── questions.py          # 题库
│   │   ├── services/
│   │   │   ├── session_store.py      # 会话持久化（SQLite）
│   │   │   └── account_store.py      # 账号 / 简历 / 看板存储
│   │   ├── models/schemas.py         # Pydantic 数据模型
│   │   └── agents/                   # Agent 编排层
│   │       ├── interviewer.py        # 面试官 Agent
│   │       ├── coach.py              # 辅导教练 Agent
│   │       ├── evaluator.py          # 评估官 Agent
│   │       ├── router.py             # 统一调度入口
│   │       └── prompts.py            # System Prompt 模板
│   ├── tests/                        # pytest 测试
│   ├── data/                         # 运行时数据（会话/向量库/上传文件）
│   ├── .env.example                  # 环境变量模板
│   └── requirements.txt
│
├── frontend/                         # Vue 3 前端
│   ├── src/
│   │   ├── App.vue                   # 根布局（PC 侧栏 / 手机底栏）
│   │   ├── views/
│   │   │   ├── Dashboard.vue         # 总览页（历史 / 得分趋势）
│   │   │   ├── Chat.vue              # 面试间（对话 / 语音 / 导出）
│   │   │   ├── Knowledge.vue         # 资料库管理
│   │   │   ├── Report.vue            # 评估报告（雷达图）
│   │   │   ├── QuestionBank.vue      # 题库
│   │   │   ├── Landing.vue           # 落地页
│   │   │   ├── Auth.vue              # 登录 / 注册
│   │   │   ├── Account.vue           # 账号中心
│   │   │   ├── Resume.vue            # 简历工坊
│   │   │   └── Jobs.vue              # 求职看板
│   │   ├── components/
│   │   │   ├── ChatMessage.vue       # 消息气泡 + 单条朗读
│   │   │   ├── RadarChart.vue        # ECharts 雷达图
│   │   │   ├── PositionPicker.vue    # 目标岗位选择
│   │   │   ├── PositionDetailModal.vue # 岗位详情弹层
│   │   │   ├── PlatformLinks.vue     # 求职平台直达
│   │   │   ├── JdInsight.vue         # JD 解读
│   │   │   ├── ResumeForm.vue        # 简历信息表单
│   │   │   ├── ResumeAnalysis.vue    # 简历匹配 / 诊断
│   │   │   ├── RingProgress.vue      # 环形进度
│   │   │   ├── Sparkline.vue         # 迷你趋势图
│   │   │   └── Icon.vue              # 图标
│   │   ├── stores/
│   │   │   ├── chat.js               # 对话状态（含 localStorage 恢复）
│   │   │   ├── knowledge.js          # 资料库状态
│   │   │   ├── catalog.js            # 岗位 / 题库状态
│   │   │   └── auth.js               # 登录态
│   │   ├── utils/                    # platforms / toast / speech
│   │   ├── composables/              # useVoiceInput / useSystemAudio
│   │   ├── worklets/recorder-processor.js # 录音 AudioWorklet
│   │   ├── api/index.js              # API 封装（fetch + SSE + TTS）
│   │   ├── router/index.js            # 路由配置（含登录守卫）
│   │   └── styles/main.css           # 全局样式（深色主题 + 响应式）
│   ├── index.html                    # PWA meta + viewport
│   ├── vite.config.js                # Vite 配置（host:true + SSE 代理）
│   └── package.json
│
├── Dockerfile                        # 容器构建
└── README.md                         # 本文件
```

### 页面路由

| 路径 | 页面 | 登录 |
|------|------|:---:|
| `/welcome` | 落地页 | 否 |
| `/login` `/register` | 登录 / 注册 | 否 |
| `/` | 总览 | 否 |
| `/chat` | 面试间 | 否 |
| `/questions` | 题库 | 否 |
| `/knowledge` | 资料库 | 否 |
| `/report` | 评估报告 | 否 |
| `/resume` | 简历工坊 | 否（保存需登录） |
| `/jobs` | 求职看板 | 是 |
| `/account` | 账号中心 | 是 |

### API 概览（前缀 `/api/v1`）

| 模块 | 端点 |
|------|------|
| auth | `POST /register` `POST /login` `POST /register/phone` `POST /login/phone` `GET/PUT/DELETE /me` |
| resume | `POST /jd/analyze` `/generate` `/match` `/diagnose` `/rewrite` `/cover-letter` `/interview-questions`；`GET/POST /saved`，`GET/DELETE /saved/{id}` |
| jobs | `GET/POST ""`，`PUT/DELETE /{job_id}` |
| positions | `GET ""` `GET /{id}` |
| questions | `GET ""` `/meta` `/random` `/practices` `/{id}`；`PUT /{id}/favorite`；`POST /{id}/practices` |
| chat / interview / evaluation / knowledge / tts / asr | 流式对话、会话与指标、评估、资料库、语音合成 / 识别 |

---

## 🧭 使用流程

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  📚 上传资料  │──►│  🎯 模拟面试  │──►│  🎓 卡壳求助  │──►│  📊 结束评估  │──►│  🔁 反复练习  │
│   (RAG)     │    │  (流式对话)   │    │  (辅导模式)   │    │  (雷达图)    │    │  (迭代提升)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

---

## 📱 手机端使用

本项目已做完整移动端适配：

### 局域网访问（开发调试）

前端 Vite 已开启 `host: true`，手机连接与电脑**同一 WiFi** 即可直接访问：

```bash
# 终端输出示例：
➜  Local:   http://localhost:5173/
➜  Network: http://192.168.1.xxx:5173/   ← 手机打开这个地址
```

> ⚠️ 若访问不到，检查电脑防火墙是否放行 5173 端口。

### 安装为 PWA

1. Chrome / Edge 打开前端地址
2. 浏览器菜单 →「添加到主屏幕」/「安装应用」
3. 桌面生成「面试私教」图标，点击即可全屏启动

---

## 🔧 开发注意事项

- **SSE 解析**：前端必须用 `/\n?\n/` 与 `/\n/` 正则切分事件，兼容 `\r\n` 与 `\n` 两种行尾
- **Pinia 响应式**：更新消息内容时需通过 `this.messages[idx]` 修改代理对象
- **流式空块**：LLM 最后一个 chunk 的 `choices` 可能为空，需跳过
- **ASR 本地模式**：首次运行自动下载 Whisper 模型（medium 约 769MB），国内网络已配置 HuggingFace 镜像

---

## 📦 生产构建

```bash
# 前端构建（产物在 frontend/dist/）
cd frontend && npm run build

# 后端生产启动（关闭 reload）
cd ../backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

生产环境建议用 **Nginx** 反代前端静态资源 + `/api` 转发到后端，并确保 SSE 响应关闭 `proxy_buffering`。

---

## 🤝 贡献

欢迎 Issue 和 Pull Request！如果你有改进建议或发现了 Bug，请提 [Issue](https://github.com/Iris-714615/InterviewAgent/issues) 讨论。

---

## 📄 License

[MIT](LICENSE)

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/Iris-714615">Iris-714615</a>
</p>


## 服务降级与 Railway 配置

资料库默认使用按会话隔离的本地关键词检索，不依赖嵌入接口，因此外部嵌入服务不可用时仍可上传和检索资料。若部署环境已配置兼容的嵌入模型，可设置 `RAG_VECTOR_ENABLED=true`，并按需指定 `EMBEDDING_API_KEY`、`EMBEDDING_BASE_URL`。向量调用超时或失败会回退到关键词检索；页面显示“本地检索”以区分检索方式。

实时面试与辅导默认使用快速模型，聊天在检索、模型首字和整轮回复上设有超时。外部模型不可用时，系统给出明确标注的基础练习问题，不会把预设问题或固定分数伪装成模型结果。浏览器优先使用本机语音朗读；不支持浏览器语音时才尝试云端语音，云端有短超时。

Railway 使用根目录 `Dockerfile` 单服务部署：先构建 `frontend/dist`，再由 FastAPI 同域托管页面与 `/api`，访问根域名即可使用。应为 `/app/data` 挂载持久化卷，以保留 SQLite 账号、会话、上传资料和检索索引；生产环境通过环境变量设置 `AUTH_SECRET`、`API_KEY`。
