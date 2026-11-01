"""岗位目录：内置多行业岗位，并支持自定义岗位。

岗位 ID 为稳定字符串，会话中直接存储；自定义岗位使用 `custom:<名称>` 形式，
描述由会话单独保存，不依赖目录。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Position:
    id: str
    name: str
    category: str
    focus: str
    skills: tuple[str, ...] = field(default_factory=tuple)
    hot: bool = False

    def to_dict(self) -> dict:
        data = asdict(self)
        data["skills"] = list(self.skills)
        return data


CATEGORIES: list[dict] = [
    {"id": "ai", "name": "人工智能", "icon": "sparkles"},
    {"id": "backend", "name": "后端与架构", "icon": "server"},
    {"id": "frontend", "name": "前端与客户端", "icon": "layout"},
    {"id": "data", "name": "数据与算法", "icon": "chart"},
    {"id": "infra", "name": "运维与安全", "icon": "shield"},
    {"id": "quality", "name": "测试与质量", "icon": "check"},
    {"id": "product", "name": "产品与设计", "icon": "compass"},
    {"id": "business", "name": "运营与市场", "icon": "megaphone"},
    {"id": "function", "name": "职能与管理", "icon": "users"},
]

_P = Position
POSITIONS: tuple[Position, ...] = (
    # ---- 人工智能 ----
    _P("ai_app_engineer", "AI 大模型应用工程师", "ai",
       "RAG 系统设计、Agent 架构、Prompt 工程、模型选型与微调、向量数据库、LangChain/LlamaIndex、上下文工程、幻觉治理、成本与延迟优化、AI 应用落地案例",
       ("RAG", "Agent", "Prompt", "向量库", "微调"), True),
    _P("ai_dev_engineer", "AI 应用开发工程师", "ai",
       "大模型 API 集成、流式输出、Function Calling、Python/FastAPI/Node 后端工程化、并发与限流、SSE/WebSocket、Token 计费、缓存策略、接口稳定性、CI/CD",
       ("FastAPI", "SSE", "Function Calling", "限流", "缓存"), True),
    _P("ai_product_manager", "AI 产品经理", "ai",
       "AI 能力边界认知、需求拆解与优先级、场景挖掘、ROI 与效果评估、Prompt 产品化、数据飞轮、用户旅程、AI 伦理与合规、商业化路径、与算法团队协作",
       ("场景挖掘", "效果评估", "数据飞轮", "合规"), True),
    _P("llm_algorithm", "大模型算法工程师", "ai",
       "Transformer 原理、预训练与 SFT、RLHF/DPO、LoRA 等参数高效微调、分布式训练、推理加速与量化、评测体系、数据清洗与配比",
       ("Transformer", "SFT", "RLHF", "LoRA", "量化"), True),
    _P("cv_engineer", "计算机视觉工程师", "ai",
       "CNN/ViT 架构、目标检测与分割、多模态模型、数据增强、模型部署与端侧优化、精度与速度权衡",
       ("检测", "分割", "ViT", "多模态", "TensorRT")),
    _P("nlp_engineer", "NLP 算法工程师", "ai",
       "文本分类与抽取、语义匹配、检索与排序、预训练模型应用、评测指标、领域适配与数据标注",
       ("NER", "语义匹配", "BERT", "排序")),
    _P("ml_platform", "机器学习平台工程师", "ai",
       "训练与推理平台建设、特征平台、模型服务化、GPU 调度、MLOps、实验管理与可观测性",
       ("MLOps", "Kubernetes", "GPU 调度", "模型服务")),
    _P("ai_solution", "AI 解决方案架构师", "ai",
       "客户需求诊断、AI 方案设计、POC 推进、私有化部署、成本测算、跨团队交付与风险把控",
       ("售前", "POC", "私有化", "方案设计")),
    # ---- 后端与架构 ----
    _P("java_backend", "Java 后端工程师", "backend",
       "Java 基础与 JVM、并发编程、Spring/Spring Boot、MySQL 索引与事务、Redis、消息队列、微服务治理、高并发系统设计",
       ("JVM", "Spring", "MySQL", "Redis", "MQ"), True),
    _P("go_backend", "Go 后端工程师", "backend",
       "Go 语言特性与 GMP 调度、channel 与并发模型、内存管理与 GC、gRPC 微服务、性能分析、云原生开发",
       ("Goroutine", "gRPC", "GC", "pprof"), True),
    _P("python_backend", "Python 后端工程师", "backend",
       "Python 语言机制、GIL 与异步、Django/FastAPI、ORM 与数据库优化、任务队列、接口设计与测试",
       ("asyncio", "FastAPI", "Django", "Celery")),
    _P("cpp_engineer", "C++ 开发工程师", "backend",
       "C++ 内存模型与智能指针、STL、模板、多线程、网络编程、性能调优与调试",
       ("STL", "RAII", "多线程", "网络编程")),
    _P("architect", "系统架构师", "backend",
       "分布式系统设计、高可用与容灾、一致性与事务、容量规划、技术选型、架构演进与治理",
       ("分布式", "高可用", "一致性", "容量规划")),
    # ---- 前端与客户端 ----
    _P("frontend", "前端开发工程师", "frontend",
       "JavaScript/TypeScript 基础、浏览器原理、Vue/React 原理、工程化与构建、性能优化、跨端方案、前端安全",
       ("TypeScript", "Vue", "React", "性能优化", "工程化"), True),
    _P("fullstack", "全栈工程师", "frontend",
       "前后端协作、接口设计、Node.js 服务、数据库建模、部署与 DevOps、端到端交付能力",
       ("Node.js", "全链路", "接口设计", "DevOps")),
    _P("android", "Android 开发工程师", "frontend",
       "Kotlin/Java、Activity 与生命周期、UI 渲染与卡顿优化、内存泄漏、Jetpack、组件化与插件化",
       ("Kotlin", "Jetpack", "性能", "组件化")),
    _P("ios", "iOS 开发工程师", "frontend",
       "Swift/Objective-C、RunLoop 与 Runtime、内存管理 ARC、UI 性能、SwiftUI、包体与启动优化",
       ("Swift", "RunLoop", "ARC", "SwiftUI")),
    _P("game_client", "游戏客户端工程师", "frontend",
       "Unity/UE 引擎、渲染管线、性能与内存优化、网络同步、热更新、游戏框架设计",
       ("Unity", "渲染", "帧同步", "热更新")),
    # ---- 数据与算法 ----
    _P("data_analyst", "数据分析师", "data",
       "SQL 与数据建模、指标体系、AB 实验、归因分析、业务洞察与可视化、数据驱动决策",
       ("SQL", "指标体系", "AB 实验", "归因"), True),
    _P("data_engineer", "大数据开发工程师", "data",
       "Hadoop/Spark/Flink、数仓分层建模、实时与离线计算、数据质量治理、调度与性能调优",
       ("Spark", "Flink", "数仓", "数据治理")),
    _P("recommend_algo", "推荐算法工程师", "data",
       "召回与排序模型、特征工程、CTR 预估、冷启动、多目标优化、线上实验与效果评估",
       ("召回", "排序", "CTR", "特征工程")),
    _P("search_algo", "搜索算法工程师", "data",
       "查询理解、倒排索引、相关性排序、向量检索、搜索评测指标与体验优化",
       ("倒排", "相关性", "向量检索", "Query 理解")),
    # ---- 运维与安全 ----
    _P("devops", "DevOps / SRE 工程师", "infra",
       "Linux 与网络、Kubernetes、CI/CD、监控告警、故障排查与复盘、SLO 与稳定性建设",
       ("Kubernetes", "CI/CD", "监控", "SLO"), True),
    _P("cloud_engineer", "云计算工程师", "infra",
       "云服务架构、IaaS/PaaS、网络与存储、成本优化、多云与混合云、基础设施即代码",
       ("云原生", "Terraform", "VPC", "成本优化")),
    _P("security", "网络安全工程师", "infra",
       "Web 安全漏洞与防护、渗透测试方法、安全架构、应急响应、合规与等保、零信任",
       ("OWASP", "渗透测试", "应急响应", "等保")),
    _P("dba", "数据库管理员", "infra",
       "MySQL/PostgreSQL 内核、备份恢复、高可用架构、SQL 调优、分库分表与迁移",
       ("MySQL", "备份恢复", "SQL 调优", "分库分表")),
    # ---- 测试与质量 ----
    _P("qa_engineer", "测试开发工程师", "quality",
       "测试设计方法、自动化测试框架、接口与性能测试、持续集成、质量度量与缺陷分析",
       ("自动化", "接口测试", "性能测试", "质量度量"), True),
    # ---- 产品与设计 ----
    _P("product_manager", "产品经理", "product",
       "用户研究、需求分析与优先级、PRD 撰写、数据分析、竞品分析、项目推进与跨团队协作、商业思维",
       ("需求分析", "PRD", "竞品分析", "数据驱动"), True),
    _P("b_product", "B 端产品经理", "product",
       "业务流程梳理、SaaS 产品设计、权限与配置体系、客户需求抽象、交付与实施",
       ("SaaS", "流程梳理", "权限体系", "客户成功")),
    _P("ui_designer", "UI / 交互设计师", "product",
       "设计原则与规范、交互流程、可用性测试、设计系统、视觉表达、与研发协作落地",
       ("Figma", "设计系统", "可用性", "交互")),
    _P("ux_researcher", "用户研究员", "product",
       "定性与定量研究方法、访谈设计、问卷与统计、用户画像、洞察输出与推动落地",
       ("访谈", "问卷", "画像", "可用性")),
    # ---- 运营与市场 ----
    _P("operations", "用户运营", "business",
       "用户分层与生命周期、增长策略、活动策划、社群运营、数据复盘与转化优化",
       ("增长", "用户分层", "活动", "复盘"), True),
    _P("content_ops", "内容运营", "business",
       "内容策略、选题与生产、分发渠道、内容数据分析、IP 与品牌调性",
       ("选题", "分发", "新媒体", "数据分析")),
    _P("marketing", "市场营销", "business",
       "品牌定位、营销策略、投放与渠道、预算与 ROI、整合营销与活动执行",
       ("品牌", "投放", "ROI", "渠道")),
    _P("sales", "销售 / 客户经理", "business",
       "客户开发与需求挖掘、谈判与成交、客户关系维护、销售漏斗管理、业绩目标拆解",
       ("客户开发", "谈判", "漏斗", "大客户")),
    # ---- 职能与管理 ----
    _P("project_manager", "项目经理", "function",
       "项目计划与范围管理、进度与风险控制、资源协调、敏捷/瀑布方法、干系人沟通、交付复盘",
       ("PMP", "敏捷", "风险管理", "干系人")),
    _P("hrbp", "HR / HRBP", "function",
       "招聘与人才评估、绩效与激励、组织发展、员工关系、业务理解与人力规划",
       ("招聘", "绩效", "组织发展", "员工关系")),
    _P("finance", "财务分析", "function",
       "财务报表分析、预算与成本管控、经营分析、财务建模、风险与合规",
       ("报表分析", "预算", "建模", "合规")),
    _P("tech_manager", "技术经理 / 团队负责人", "function",
       "团队搭建与人才培养、技术规划、研发流程与效能、跨团队协作、绩效管理与决策",
       ("团队管理", "技术规划", "研发效能", "决策"), True),
)

POSITION_MAP: dict[str, Position] = {p.id: p for p in POSITIONS}
CUSTOM_PREFIX = "custom:"
DEFAULT_POSITION = "ai_app_engineer"


def normalize_direction(value: str | None) -> str:
    """规范化岗位 ID；空值回退默认，自定义岗位保留名称。"""
    value = (value or "").strip()
    if not value:
        return DEFAULT_POSITION
    if value in POSITION_MAP:
        return value
    if value.startswith(CUSTOM_PREFIX):
        name = value[len(CUSTOM_PREFIX):].strip()[:40]
        return f"{CUSTOM_PREFIX}{name}" if name else DEFAULT_POSITION
    # 允许直接传入岗位名称，匹配目录或视为自定义
    for p in POSITIONS:
        if p.name == value:
            return p.id
    return f"{CUSTOM_PREFIX}{value[:40]}"


def position_name(direction: str) -> str:
    if direction in POSITION_MAP:
        return POSITION_MAP[direction].name
    if direction.startswith(CUSTOM_PREFIX):
        return direction[len(CUSTOM_PREFIX):]
    return direction


def position_category(direction: str) -> str | None:
    p = POSITION_MAP.get(direction)
    return p.category if p else None


def describe_position(direction: str, custom_description: str | None = None) -> str:
    """生成用于提示词的岗位描述。"""
    if direction in POSITION_MAP:
        p = POSITION_MAP[direction]
        text = f"{p.name}。重点考察:{p.focus}。"
    else:
        name = position_name(direction)
        text = f"{name}。请结合该岗位在行业中的典型职责与能力要求,覆盖专业技能、项目经验与通用素质。"
    if custom_description:
        text += f"\n岗位补充说明:{custom_description.strip()[:600]}"
    return text


def list_positions(category: str | None = None, keyword: str | None = None) -> list[dict]:
    keyword = (keyword or "").strip().lower()
    result = []
    for p in POSITIONS:
        if category and p.category != category:
            continue
        if keyword and keyword not in (p.name + p.focus + " ".join(p.skills)).lower():
            continue
        result.append(p.to_dict())
    return result
