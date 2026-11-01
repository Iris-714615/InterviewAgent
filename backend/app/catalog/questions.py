"""面试题库：覆盖各岗位类别的技术题，以及通用 HR 面、行为面题目。

题目 ID 稳定，用于收藏和练习记录。`positions` 为空表示适用于整个类别；
`category="general"` 表示通用题，适用于所有岗位（含自定义岗位）。
"""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field

from app.catalog.positions import CUSTOM_PREFIX, POSITION_MAP, normalize_direction

TYPES = {"technical": "专业技术", "hr": "HR 面", "behavioral": "行为面"}
DIFFICULTIES = {"easy": "基础", "medium": "进阶", "hard": "挑战"}


@dataclass(frozen=True)
class Question:
    id: str
    category: str
    type: str
    difficulty: str
    title: str
    tags: tuple[str, ...] = field(default_factory=tuple)
    key_points: tuple[str, ...] = field(default_factory=tuple)
    answer_outline: str = ""
    positions: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        data = asdict(self)
        for key in ("tags", "key_points", "positions"):
            data[key] = list(data[key])
        data["type_name"] = TYPES[self.type]
        data["difficulty_name"] = DIFFICULTIES[self.difficulty]
        return data


def _q(qid: str, category: str, qtype: str, difficulty: str, title: str, tags: str,
       key_points: str, outline: str, positions: str = "") -> Question:
    """紧凑构造：tags/key_points/positions 用分隔符拼接，便于维护大量数据。"""
    return Question(qid, category, qtype, difficulty, title,
                    tuple(t for t in tags.split(",") if t),
                    tuple(k for k in key_points.split("|") if k), outline,
                    tuple(p for p in positions.split(",") if p))


QUESTIONS: tuple[Question, ...] = (
    # ================= 人工智能 =================
    _q("ai-001", "ai", "technical", "medium", "请完整讲一下 RAG 系统的链路，以及每个环节最容易出问题的地方。",
       "RAG,检索,向量库", "文档解析与切分策略|Embedding 选型与召回|重排序与上下文拼接|幻觉与引用校验|离线评估指标",
       "按「数据处理 → 召回 → 重排 → 生成 → 评估」展开，每个环节给出一个真实踩坑和量化改进。",
       "ai_app_engineer,ai_dev_engineer,nlp_engineer,ai_solution"),
    _q("ai-002", "ai", "technical", "medium", "文档切分的 chunk size 和 overlap 怎么定？有没有做过对比实验？",
       "RAG,切分", "语义完整性与召回粒度的权衡|按结构切分 vs 固定长度|评估集与命中率对比",
       "说明业务文档特点，给出至少两组参数的召回率/答案准确率对比，并解释最终选择。",
       "ai_app_engineer,ai_dev_engineer"),
    _q("ai-003", "ai", "technical", "hard", "如何评估一个 LLM 应用的效果？离线和线上分别看哪些指标？",
       "评估,LLMOps", "构建评测集|自动评估与人工评估|忠实度/相关性/完整性|线上满意度与转化|回归测试",
       "先定义业务成功标准，再讲评测集构建、自动化打分方式，以及上线后的监控与回滚机制。"),
    _q("ai-004", "ai", "technical", "medium", "Function Calling / Tool Use 的原理是什么？如何保证工具调用的稳定性？",
       "Agent,工具调用", "JSON Schema 约束|参数校验与重试|失败降级|调用审计",
       "讲清模型如何输出结构化调用，再说明校验、超时、幂等与兜底策略。",
       "ai_app_engineer,ai_dev_engineer,ai_solution"),
    _q("ai-005", "ai", "technical", "hard", "设计一个多 Agent 协作系统，如何拆分职责、控制成本和避免死循环？",
       "Agent,架构", "规划/执行/反思角色|状态机与最大步数|共享记忆|成本预算与模型路由",
       "从业务场景出发画出 Agent 拓扑，说明终止条件、上下文传递和可观测性。",
       "ai_app_engineer,ai_dev_engineer"),
    _q("ai-006", "ai", "technical", "medium", "你是怎么降低大模型调用成本和延迟的？",
       "成本,性能", "模型分级路由|Prompt 压缩|缓存|流式输出|批处理",
       "给出优化前后的成本与 P95 延迟对比，并说明对效果的影响如何验证。"),
    _q("ai-007", "ai", "technical", "medium", "如何减少大模型幻觉？请结合你做过的项目说明。",
       "幻觉,可靠性", "检索增强与引用|约束输出格式|自洽性校验|拒答策略",
       "先区分事实性幻觉与指令偏离，再讲具体手段和效果数据。"),
    _q("ai-008", "ai", "technical", "hard", "LoRA 微调的原理是什么？什么场景应该微调而不是用 RAG？",
       "微调,LoRA", "低秩分解|可训练参数量|数据质量|微调 vs RAG 的适用边界",
       "讲清原理后，用「知识更新频率、风格一致性、成本」三个维度对比两种方案。",
       "llm_algorithm,nlp_engineer,ai_dev_engineer"),
    _q("ai-009", "ai", "technical", "hard", "Transformer 的自注意力复杂度是多少？长上下文有哪些优化方法？",
       "Transformer,长上下文", "O(n²) 复杂度|KV Cache|FlashAttention|位置编码外推|稀疏注意力",
       "先推导复杂度来源，再按工程优化和模型结构优化两类展开。",
       "llm_algorithm,nlp_engineer"),
    _q("ai-010", "ai", "technical", "hard", "大模型推理部署时，如何提升吞吐？vLLM 解决了什么问题？",
       "推理,部署", "PagedAttention|Continuous Batching|量化|张量并行",
       "说明显存瓶颈与批处理调度问题，再讲 vLLM 的核心机制和实际压测数据。",
       "llm_algorithm,ml_platform"),
    _q("ai-011", "ai", "technical", "medium", "目标检测中 one-stage 和 two-stage 方法的区别是什么？",
       "CV,检测", "R-CNN 系列|YOLO 系列|速度与精度权衡|Anchor-free",
       "对比两类方法的结构、典型模型和适用场景，结合项目说明选型理由。", "cv_engineer"),
    _q("ai-012", "ai", "technical", "medium", "如何处理训练数据中的类别不平衡问题？",
       "机器学习,数据", "重采样|损失加权与 Focal Loss|数据增强|评估指标选择",
       "从数据、损失、评估三个层面回答，强调不能只看准确率。",
       "cv_engineer,nlp_engineer,llm_algorithm,recommend_algo"),
    _q("ai-013", "ai", "technical", "medium", "作为 AI 产品经理，如何判断一个需求是否适合用大模型来做？",
       "AI产品,需求", "容错率|数据可得性|成本收益|可评估性|替代方案",
       "给出判断框架，再用一个做过或拒绝过的需求举例。", "ai_product_manager"),
    _q("ai-014", "ai", "technical", "medium", "AI 产品的效果指标应该怎么定义？如何和业务指标挂钩？",
       "AI产品,指标", "模型指标 vs 体验指标 vs 业务指标|Badcase 分析|A/B 实验",
       "搭建三层指标体系，说明如何通过 badcase 闭环持续迭代。", "ai_product_manager"),
    _q("ai-015", "ai", "technical", "hard", "企业客户要落地私有化大模型方案，你会如何做方案设计与 POC？",
       "解决方案,私有化", "需求调研|模型与硬件选型|安全合规|POC 成功标准|交付计划",
       "按售前调研、方案设计、POC 验证、规模化交付四步展开。", "ai_solution"),
    _q("ai-016", "ai", "technical", "medium", "训练平台如何管理 GPU 资源，提高利用率？",
       "平台,GPU", "调度策略|任务优先级与抢占|弹性伸缩|监控与成本核算",
       "说明资源现状与瓶颈，再讲调度和监控改进及利用率提升数据。", "ml_platform"),

    # ================= 后端与架构 =================
    _q("be-001", "backend", "technical", "medium", "接口响应变慢，你会如何一步步定位问题？",
       "性能,排障", "监控与链路追踪|慢查询|线程/协程阻塞|GC|下游依赖",
       "按「确认现象 → 缩小范围 → 定位根因 → 修复验证 → 复盘」展开，给出真实案例。"),
    _q("be-002", "backend", "technical", "medium", "如何保证缓存和数据库的数据一致性？",
       "缓存,一致性", "Cache Aside|先更新库再删缓存|延迟双删|binlog 订阅|过期兜底",
       "对比几种方案的一致性窗口与复杂度，说明自己项目的选择。"),
    _q("be-003", "backend", "technical", "medium", "缓存穿透、击穿、雪崩分别是什么？怎么解决？",
       "缓存,高并发", "布隆过滤器与空值缓存|互斥锁与热点永不过期|过期时间打散与多级缓存",
       "三个问题分别给出成因与解决方案，最好结合压测或线上事故说明。"),
    _q("be-004", "backend", "technical", "hard", "设计一个秒杀系统，如何应对瞬时高并发？",
       "系统设计,高并发", "流量削峰|库存预扣|异步下单|限流熔断|防刷",
       "从前端到存储分层说明，每层给出容量估算与降级手段。"),
    _q("be-005", "backend", "technical", "medium", "MySQL 索引为什么用 B+ 树？什么情况下索引会失效？",
       "MySQL,索引", "B+ 树特性与磁盘 IO|最左前缀|函数与隐式转换|回表与覆盖索引",
       "先讲数据结构原因，再列举失效场景并给出 explain 分析思路。",
       "java_backend,go_backend,python_backend,dba,architect"),
    _q("be-006", "backend", "technical", "hard", "分布式事务有哪些方案？你在项目中是怎么选的？",
       "分布式,事务", "2PC/3PC|TCC|Saga|本地消息表|最终一致性",
       "对比各方案的一致性、性能与侵入性，结合业务说明取舍。"),
    _q("be-007", "backend", "technical", "medium", "消息队列如何保证消息不丢失、不重复消费？",
       "消息队列", "生产者确认|持久化与副本|消费者手动提交|幂等设计",
       "按生产、存储、消费三端说明，并给出幂等实现方式。"),
    _q("be-008", "backend", "technical", "medium", "JVM 内存结构和常见垃圾回收器有哪些？如何排查 OOM？",
       "Java,JVM", "堆/栈/元空间|G1 与 ZGC|GC 日志|堆转储分析", "讲清结构与回收器差异，再给出 OOM 排查步骤。",
       "java_backend"),
    _q("be-009", "backend", "technical", "medium", "Spring 的 Bean 生命周期和事务失效场景有哪些？",
       "Java,Spring", "实例化/属性注入/初始化/销毁|代理机制|自调用失效|异常类型",
       "结合 AOP 代理原理解释事务失效的根因。", "java_backend"),
    _q("be-010", "backend", "technical", "medium", "Go 的 GMP 调度模型是怎样的？goroutine 泄漏如何排查？",
       "Go,并发", "G/M/P 职责|工作窃取|阻塞系统调用|pprof", "先讲调度模型，再给出泄漏场景和 pprof 定位方法。",
       "go_backend"),
    _q("be-011", "backend", "technical", "medium", "Python 的 GIL 是什么？异步 IO 适合什么场景？",
       "Python,并发", "GIL 与 CPU 密集任务|多进程|asyncio 事件循环|IO 密集场景",
       "说明 GIL 影响边界，再讲 asyncio 原理与项目中的使用。", "python_backend"),
    _q("be-012", "backend", "technical", "hard", "C++ 智能指针有哪些？循环引用怎么处理？",
       "C++,内存", "unique_ptr/shared_ptr/weak_ptr|引用计数|RAII", "讲清所有权语义，用 weak_ptr 打破循环。",
       "cpp_engineer,game_client"),
    _q("be-013", "backend", "technical", "hard", "如何把一个单体应用拆分为微服务？拆分原则是什么？",
       "架构,微服务", "领域驱动划分|数据拆分|服务治理|灰度迁移|拆分代价",
       "讲拆分依据和迁移路径，并说明什么时候不该拆。", "architect,java_backend,go_backend,tech_manager"),
    _q("be-014", "backend", "technical", "medium", "如何设计一个高可用的接口限流方案？",
       "限流,高可用", "令牌桶/漏桶|单机与分布式限流|动态配置|降级与提示",
       "对比算法后给出分布式实现与配置方式。"),

    # ================= 前端与客户端 =================
    _q("fe-001", "frontend", "technical", "medium", "浏览器从输入 URL 到页面渲染完成发生了什么？",
       "浏览器,网络", "DNS 与 TCP/TLS|HTTP 缓存|解析 DOM/CSSOM|布局与绘制|合成",
       "按网络阶段和渲染阶段讲清，再落到可优化点。", "frontend,fullstack"),
    _q("fe-002", "frontend", "technical", "medium", "你做过哪些前端性能优化？如何衡量效果？",
       "性能,Web Vitals", "LCP/INP/CLS|代码分割与懒加载|资源压缩与缓存|长任务拆分",
       "先讲指标与监控方式，再给优化手段和前后数据。", "frontend,fullstack"),
    _q("fe-003", "frontend", "technical", "medium", "Vue 3 的响应式原理是什么？和 Vue 2 有何不同？",
       "Vue,响应式", "Proxy vs defineProperty|依赖收集与触发|ref 与 reactive|调度队列",
       "讲清 track/trigger 流程，说明 Proxy 带来的能力提升。", "frontend,fullstack"),
    _q("fe-004", "frontend", "technical", "medium", "React 的 Hooks 为什么不能写在条件语句里？如何避免不必要的渲染？",
       "React,Hooks", "Hooks 链表顺序|memo/useMemo/useCallback|状态下沉与拆分",
       "从 Fiber 上 Hooks 存储方式解释规则，再讲渲染优化。", "frontend,fullstack"),
    _q("fe-005", "frontend", "technical", "hard", "如何设计一个大型前端项目的工程化体系？",
       "工程化,架构", "Monorepo|组件库与设计规范|CI/CD|质量门禁|监控告警",
       "从开发、构建、发布、监控四个环节说明。", "frontend,fullstack"),
    _q("fe-006", "frontend", "technical", "medium", "常见的前端安全问题有哪些？如何防范 XSS 和 CSRF？",
       "安全", "输入输出转义|CSP|SameSite Cookie|CSRF Token", "分别说明攻击原理与防御措施。",
       "frontend,fullstack"),
    _q("fe-007", "frontend", "technical", "medium", "Android 中 Activity 的生命周期和启动模式有哪些？",
       "Android", "生命周期回调|standard/singleTop/singleTask/singleInstance|任务栈",
       "讲清回调时机，并结合场景说明启动模式选择。", "android"),
    _q("fe-008", "frontend", "technical", "hard", "如何排查和优化 App 的卡顿与内存泄漏？",
       "移动端,性能", "主线程耗时|帧率监控|LeakCanary/Instruments|图片内存",
       "给出工具链与具体案例，说明优化前后数据。", "android,ios"),
    _q("fe-009", "frontend", "technical", "medium", "iOS 中 ARC 是如何工作的？block 循环引用如何避免？",
       "iOS,内存", "引用计数|strong/weak|weak-strong dance", "说明 ARC 插入 retain/release 的机制和循环引用场景。",
       "ios"),
    _q("fe-010", "frontend", "technical", "hard", "游戏客户端如何优化 Draw Call 和帧率？",
       "游戏,渲染", "合批|图集|LOD|对象池|性能分析工具", "从 CPU 与 GPU 两侧分别说明瓶颈与优化。",
       "game_client"),
    _q("fe-011", "frontend", "technical", "medium", "全栈项目中，你如何设计前后端接口和鉴权方案？",
       "全栈,接口", "RESTful/GraphQL|JWT 与 Session|刷新令牌|接口版本管理",
       "结合项目说明接口规范、鉴权流程与安全考虑。", "fullstack"),

    # ================= 数据与算法 =================
    _q("da-001", "data", "technical", "medium", "某个核心指标突然下跌 10%，你会如何分析？",
       "数据分析,归因", "确认数据口径|维度拆解|内外部因素|假设验证|结论与建议",
       "按「确认真实性 → 拆解定位 → 归因验证 → 给出行动」回答。",
       "data_analyst,product_manager,operations"),
    _q("da-002", "data", "technical", "medium", "A/B 实验如何设计？如何判断结果是否显著？",
       "实验,统计", "实验单元与分流|样本量估算|假设检验|多重比较|新奇效应",
       "讲完整流程，强调样本量与实验周期，避免常见误判。",
       "data_analyst,product_manager,recommend_algo,search_algo"),
    _q("da-003", "data", "technical", "medium", "SQL 中如何计算用户连续登录天数？",
       "SQL", "窗口函数|日期减行号分组|去重", "用 row_number 与日期差构造分组键，再聚合。",
       "data_analyst,data_engineer"),
    _q("da-004", "data", "technical", "medium", "数据仓库为什么要分层？你们是怎么建模的？",
       "数仓,建模", "ODS/DWD/DWS/ADS|维度建模|星型与雪花模型|口径统一",
       "说明分层价值，再结合项目讲主题域与建模方式。", "data_engineer"),
    _q("da-005", "data", "technical", "hard", "Spark 任务数据倾斜如何定位和解决？",
       "大数据,Spark", "Stage 耗时分析|热点 key|加盐打散|广播 Join|两阶段聚合",
       "先讲定位方法，再按场景给出解决方案。", "data_engineer"),
    _q("da-006", "data", "technical", "hard", "推荐系统的召回、粗排、精排各自的作用和常用模型是什么？",
       "推荐", "多路召回|双塔模型|CTR 预估|多目标排序|重排与多样性",
       "按漏斗结构讲职责，结合项目讲模型迭代收益。", "recommend_algo"),
    _q("da-007", "data", "technical", "hard", "推荐系统中如何解决冷启动问题？",
       "推荐,冷启动", "用户冷启动|物品冷启动|内容特征|探索与利用", "分用户与物品两侧，给出策略与效果评估方式。",
       "recommend_algo"),
    _q("da-008", "data", "technical", "hard", "搜索相关性如何建模和评估？",
       "搜索", "BM25|语义匹配|Query 理解|NDCG 等指标|人工标注", "从召回到排序讲相关性建模，再说明评估体系。",
       "search_algo"),
    _q("da-009", "data", "technical", "medium", "如何搭建一套业务指标体系？",
       "指标体系", "北极星指标|指标拆解|口径管理|看板与预警", "用 OSM 或 AARRR 框架拆解，说明落地与治理。",
       "data_analyst"),

    # ================= 运维与安全 =================
    _q("op-001", "infra", "technical", "medium", "线上服务突然不可用，你的应急处理流程是什么？",
       "应急,SRE", "止损优先|快速回滚|影响评估|根因分析|复盘改进",
       "强调先恢复再定位，说明沟通机制与复盘产出。"),
    _q("op-002", "infra", "technical", "medium", "Kubernetes 中 Pod 一直处于 CrashLoopBackOff，如何排查？",
       "K8s", "kubectl describe/logs|探针配置|资源限制|镜像与配置错误", "给出命令级的排查步骤。",
       "devops,cloud_engineer"),
    _q("op-003", "infra", "technical", "hard", "如何设计一套 CI/CD 与灰度发布体系？",
       "CI/CD,发布", "流水线阶段|制品管理|金丝雀与蓝绿|自动回滚|发布审计",
       "从提交代码到线上全流程讲，并说明质量门禁。", "devops,cloud_engineer"),
    _q("op-004", "infra", "technical", "medium", "如何建设监控与告警体系，避免告警风暴？",
       "可观测性", "指标/日志/链路|SLO 与 SLI|告警分级与收敛|值班机制",
       "围绕 SLO 设计告警，说明降噪方法。", "devops,cloud_engineer"),
    _q("op-005", "infra", "technical", "hard", "多云/混合云架构下如何做成本优化与容灾？",
       "云架构", "资源规划|预留与竞价实例|跨可用区部署|RTO/RPO", "给出成本与可用性双目标的方案。",
       "cloud_engineer,architect"),
    _q("op-006", "infra", "technical", "medium", "常见 Web 漏洞有哪些？SQL 注入如何防御？",
       "安全,漏洞", "OWASP Top 10|参数化查询|最小权限|WAF", "讲原理、攻击示例和多层防御。",
       "security"),
    _q("op-007", "infra", "technical", "hard", "如何在企业内部推进安全开发生命周期（SDL）？",
       "安全,SDL", "威胁建模|代码审计与扫描|安全培训|应急响应", "从流程、工具、组织三方面说明。",
       "security"),
    _q("op-008", "infra", "technical", "hard", "数据库主从延迟大如何处理？如何做在线大表变更？",
       "数据库,运维", "复制原理|并行复制|读写分离策略|gh-ost/pt-osc", "分析延迟原因并给出处理与变更方案。",
       "dba"),

    # ================= 测试与质量 =================
    _q("qa-001", "quality", "technical", "easy", "给你一个登录功能，你会如何设计测试用例？",
       "测试设计", "功能与边界|异常输入|安全|性能|兼容性", "用等价类、边界值等方法系统覆盖，体现思考维度。"),
    _q("qa-002", "quality", "technical", "medium", "如何搭建接口自动化测试框架？如何保证用例的可维护性？",
       "自动化", "分层设计|数据驱动|环境隔离|CI 集成|报告", "讲框架结构、用例管理和稳定性治理。"),
    _q("qa-003", "quality", "technical", "medium", "性能测试如何设计？如何分析瓶颈？",
       "性能测试", "场景与指标|压测工具|梯度加压|资源监控|瓶颈定位", "从目标定义讲到结果分析与调优建议。"),
    _q("qa-004", "quality", "technical", "hard", "如何评估和测试一个大模型应用的质量？",
       "AI测试", "评测集|一致性与鲁棒性|安全与越狱|回归对比", "说明 AI 应用测试与传统测试的差异与方法。"),
    _q("qa-005", "quality", "technical", "medium", "线上出现了测试没发现的 Bug，你会怎么复盘？",
       "质量,复盘", "漏测原因|流程改进|用例补充|质量度量", "客观分析原因，给出可落地的改进措施。"),

    # ================= 产品与设计 =================
    _q("pd-001", "product", "technical", "medium", "如何判断一个需求是否值得做？优先级如何排？",
       "需求管理", "用户价值与商业价值|成本评估|RICE/KANO|数据验证",
       "给出判断框架与优先级方法，用真实案例说明。", "product_manager,b_product,ai_product_manager"),
    _q("pd-002", "product", "technical", "medium", "讲一个你从 0 到 1 负责的功能，如何验证它成功了？",
       "产品设计", "问题定义|方案设计|上线指标|迭代", "按 STAR 讲完整链路，突出数据结果和复盘。",
       "product_manager,b_product,ai_product_manager"),
    _q("pd-003", "product", "technical", "medium", "如果让你优化某款常用 App 的一个功能，你会怎么做？",
       "产品分析", "用户场景|痛点分析|竞品对比|方案与指标", "选具体功能，结构化给出分析和改进方案。",
       "product_manager,ux_researcher"),
    _q("pd-004", "product", "technical", "hard", "B 端产品如何平衡定制化需求和产品标准化？",
       "B端", "客户分层|配置化与插件化|需求池管理|商业影响", "说明判断标准与产品架构上的应对。", "b_product"),
    _q("pd-005", "product", "technical", "medium", "讲一个你最满意的设计作品，你的设计决策依据是什么？",
       "设计", "用户研究|信息架构|视觉规范|可用性测试|数据验证", "围绕问题与目标讲设计过程，而不只是视觉结果。",
       "ui_designer,ux_researcher"),
    _q("pd-006", "product", "technical", "medium", "如何建立和维护一套设计系统？",
       "设计系统", "设计 Token|组件规范|协作流程|版本治理", "说明设计系统价值、落地过程与推广方式。", "ui_designer"),
    _q("pd-007", "product", "technical", "medium", "用户访谈如何设计？如何避免引导性问题？",
       "用户研究", "研究目标|样本选择|开放式提问|洞察提炼", "讲访谈提纲设计与结论产出方式。", "ux_researcher"),

    # ================= 运营与市场 =================
    _q("bs-001", "business", "technical", "medium", "如何策划一场拉新活动？如何评估活动效果？",
       "活动运营", "目标与预算|渠道与玩法|风控防刷|ROI 复盘", "按目标、方案、执行、复盘展开，给出数据。",
       "operations,marketing"),
    _q("bs-002", "business", "technical", "medium", "用户留存下降，你会从哪些方面着手提升？",
       "用户运营", "留存曲线分析|用户分层|激励与触达|产品体验", "先诊断再分层施策，说明验证方式。", "operations"),
    _q("bs-003", "business", "technical", "medium", "你如何判断一篇内容是否优质？如何打造爆款？",
       "内容运营", "选题|用户需求|传播机制|数据反馈", "结合做过的内容案例，讲方法论和数据表现。", "content_ops"),
    _q("bs-004", "business", "technical", "medium", "品牌营销预算有限时，如何选择投放渠道？",
       "营销,投放", "目标人群|渠道特性|CAC 与 LTV|归因分析", "说明渠道测试与预算分配的逻辑。", "marketing"),
    _q("bs-005", "business", "technical", "medium", "讲一个你签下的最难的客户，你是如何推进的？",
       "销售", "需求挖掘|决策链|异议处理|促成成交", "按销售阶段讲关键动作与结果。", "sales"),
    _q("bs-006", "business", "technical", "medium", "如何制定季度销售目标并拆解到执行？",
       "销售管理", "目标拆解|漏斗管理|客户分级|过程复盘", "给出漏斗模型与跟进节奏。", "sales"),

    # ================= 职能与管理 =================
    _q("fn-001", "function", "technical", "medium", "项目延期风险很大时，你会如何处理？",
       "项目管理", "风险识别|范围与资源调整|干系人沟通|里程碑重排", "强调尽早暴露、给出备选方案和沟通方式。",
       "project_manager,tech_manager"),
    _q("fn-002", "function", "technical", "medium", "如何管理跨部门协作中的冲突和优先级不一致？",
       "协作", "目标对齐|共识机制|升级路径|透明信息", "结合案例说明如何达成一致并推进落地。",
       "project_manager,hrbp,tech_manager"),
    _q("fn-003", "function", "technical", "medium", "作为 HRBP，如何支撑业务部门的组织发展？",
       "HRBP", "业务理解|组织诊断|人才盘点|激励机制", "从业务目标出发讲 HR 举措与效果。", "hrbp"),
    _q("fn-004", "function", "technical", "medium", "如何做一次预算编制与执行分析？",
       "财务", "预算口径|滚动预测|差异分析|业务沟通", "讲预算流程与分析框架，结合实际案例。", "finance"),
    _q("fn-005", "function", "technical", "hard", "你如何带团队？如何处理绩效不佳的成员？",
       "团队管理", "目标设定|辅导与反馈|绩效改进计划|团队氛围", "说明管理理念并给出具体案例。", "tech_manager"),
    _q("fn-006", "function", "technical", "hard", "技术债务和业务需求冲突时，你如何决策？",
       "技术管理", "风险量化|分阶段偿还|与业务沟通|资源配比", "用数据说明技术债影响，给出平衡方案。",
       "tech_manager,architect"),

    # ================= 通用 · 专业能力（自定义岗位兜底） =================
    _q("gn-001", "general", "technical", "easy", "请介绍一个你最有代表性的项目，你在其中承担了什么角色？",
       "项目经历", "背景与目标|个人职责|关键难点|结果数据", "用 STAR 结构讲，突出个人贡献与量化结果。"),
    _q("gn-002", "general", "technical", "medium", "你在专业领域里遇到过最难的问题是什么？如何解决的？",
       "问题解决", "问题定义|分析过程|方案对比|结果与复盘", "体现系统化思考，而不只是结论。"),
    _q("gn-003", "general", "technical", "medium", "这个岗位最核心的能力是什么？你如何证明自己具备？",
       "岗位理解", "岗位认知|能力匹配|证据案例", "先说明对岗位的理解，再用案例逐条匹配。"),
    _q("gn-004", "general", "technical", "medium", "如果入职后接手一个陌生领域的任务，你会如何快速上手？",
       "学习能力", "信息收集|请教与对齐|小步验证|沉淀", "给出方法与过往快速学习的实例。"),

    # ================= 通用 · HR 面 =================
    _q("hr-001", "general", "hr", "easy", "请做一个简短的自我介绍。", "自我介绍",
       "1-2 分钟|与岗位相关的经历|核心优势|求职动机", "按「我是谁 → 做过什么 → 为何适合 → 为何选择这里」组织。"),
    _q("hr-002", "general", "hr", "easy", "你为什么离开上一家公司？", "离职原因",
       "客观积极|不抱怨前东家|与新岗位关联", "聚焦职业发展诉求，并说明与本岗位的匹配。"),
    _q("hr-003", "general", "hr", "easy", "为什么选择我们公司和这个岗位？", "求职动机",
       "了解公司业务|岗位匹配|个人规划", "体现事先调研，结合个人能力与发展方向回答。"),
    _q("hr-004", "general", "hr", "medium", "你未来 3-5 年的职业规划是什么？", "职业规划",
       "方向清晰|可落地|与公司发展契合", "给出阶段性目标，说明如何在岗位上实现。"),
    _q("hr-005", "general", "hr", "medium", "你最大的优点和缺点分别是什么？", "自我认知",
       "优点有案例支撑|缺点真实且在改进|不避重就轻", "缺点要说明已采取的改进行动与效果。"),
    _q("hr-006", "general", "hr", "medium", "你的期望薪资是多少？依据是什么？", "薪资",
       "市场行情|个人价值|弹性空间", "给出合理区间与依据，同时表达对整体机会的重视。"),
    _q("hr-007", "general", "hr", "medium", "你如何看待加班？如何平衡工作与生活？", "价值观",
       "理解业务节奏|效率优先|自我管理", "表达责任感，同时体现高效工作的方法。"),
    _q("hr-008", "general", "hr", "medium", "如果同时拿到多个 offer，你会如何选择？", "决策",
       "选择标准|发展优先级|真诚", "给出清晰的决策维度，体现对本岗位的意向。"),
    _q("hr-009", "general", "hr", "easy", "你有什么问题想问我们吗？", "反问",
       "团队与业务|岗位期望|成长路径", "准备 2-3 个有深度的问题，避免只问福利。"),
    _q("hr-010", "general", "hr", "medium", "你过去的工作经历中，有没有空窗期？做了什么？", "经历",
       "坦诚说明|学习与成长|重新出发的准备", "说明空窗原因与期间的积累。"),

    # ================= 通用 · 行为面 =================
    _q("bh-001", "general", "behavioral", "medium", "讲一次你和同事意见严重分歧的经历，最后如何解决？", "冲突处理",
       "情境与分歧点|沟通方式|共识达成|结果与反思", "用 STAR 结构，体现对事不对人和数据驱动的沟通。"),
    _q("bh-002", "general", "behavioral", "medium", "讲一次你失败的经历，你从中学到了什么？", "失败复盘",
       "真实失败|个人责任|改进行动|后续应用", "不推卸责任，重点讲反思与之后的改变。"),
    _q("bh-003", "general", "behavioral", "medium", "讲一次你在资源不足、时间很紧的情况下完成任务的经历。", "抗压,执行力",
       "优先级排序|资源争取|风险管理|结果", "说明如何拆解与取舍，给出结果数据。"),
    _q("bh-004", "general", "behavioral", "hard", "讲一次你在没有职权的情况下推动跨团队协作的经历。", "影响力",
       "目标对齐|利益相关方|推动手段|结果", "体现影响力而非依赖职权，说明关键推进动作。"),
    _q("bh-005", "general", "behavioral", "medium", "讲一次你主动发现并解决问题、超出职责范围的经历。", "主动性",
       "发现问题|主动推动|结果|价值", "强调主人翁意识与产生的实际价值。"),
    _q("bh-006", "general", "behavioral", "medium", "讲一次你需要快速学习新技能来完成任务的经历。", "学习能力",
       "学习路径|时间投入|应用效果", "给出具体学习方法与产出。"),
    _q("bh-007", "general", "behavioral", "medium", "讲一次你收到负面反馈的经历，你是如何应对的？", "反馈,成长",
       "接受反馈|分析原因|改进行动|后续结果", "体现开放心态与持续改进。"),
    _q("bh-008", "general", "behavioral", "hard", "讲一次你需要在信息不完整的情况下做出重要决策的经历。", "决策",
       "信息收集|风险评估|决策依据|结果复盘", "说明如何在不确定性下降低风险并跟踪结果。"),
    _q("bh-009", "general", "behavioral", "medium", "讲一次你帮助团队成员成长或提升团队效率的经历。", "团队协作",
       "识别问题|帮助方式|效果", "具体说明行动与可量化的团队收益。"),
    _q("bh-010", "general", "behavioral", "medium", "讲一次你面对客户或用户强烈不满时的处理经历。", "沟通,客户导向",
       "共情倾听|问题定位|解决方案|关系修复", "体现以用户为中心与问题闭环。"),
)

QUESTION_MAP: dict[str, Question] = {q.id: q for q in QUESTIONS}


def _matches_position(q: Question, direction: str) -> int:
    """匹配度：2=明确指定岗位，1=同类别通用，0=不匹配。"""
    position = POSITION_MAP.get(direction)
    if position and direction in q.positions:
        return 2
    if position and q.category == position.category and not q.positions:
        return 1
    return 0


def list_questions(*, category: str | None = None, position: str | None = None, qtype: str | None = None,
                   difficulty: str | None = None, keyword: str | None = None, tag: str | None = None,
                   ids: set[str] | None = None) -> list[Question]:
    result = []
    norm_position = normalize_direction(position) if position else None
    kw = (keyword or "").strip().lower()
    for q in QUESTIONS:
        if category and q.category != category:
            continue
        if norm_position and q.category != "general" and not _matches_position(q, norm_position):
            continue
        if qtype and q.type != qtype:
            continue
        if difficulty and q.difficulty != difficulty:
            continue
        if tag and tag not in q.tags:
            continue
        if ids is not None and q.id not in ids:
            continue
        if kw and kw not in (q.title + " " + " ".join(q.tags) + " " + " ".join(q.key_points)).lower():
            continue
        result.append(q)
    if norm_position:
        result.sort(key=lambda q: -_matches_position(q, norm_position))
    return result


def get_question(question_id: str) -> Question | None:
    return QUESTION_MAP.get(question_id)


def random_questions(count: int = 5, seed: int | None = None, **filters) -> list[Question]:
    pool = list_questions(**filters)
    rng = random.Random(seed)
    return rng.sample(pool, min(count, len(pool)))


def question_stats() -> dict:
    by_type: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_difficulty: dict[str, int] = {}
    tags: dict[str, int] = {}
    for q in QUESTIONS:
        by_type[q.type] = by_type.get(q.type, 0) + 1
        by_category[q.category] = by_category.get(q.category, 0) + 1
        by_difficulty[q.difficulty] = by_difficulty.get(q.difficulty, 0) + 1
        for t in q.tags:
            tags[t] = tags.get(t, 0) + 1
    top_tags = sorted(tags.items(), key=lambda x: -x[1])[:24]
    return {"total": len(QUESTIONS), "by_type": by_type, "by_category": by_category,
            "by_difficulty": by_difficulty, "tags": [{"name": k, "count": v} for k, v in top_tags]}


def questions_for_interview(direction: str, role: str) -> list[Question]:
    """为一场面试挑选有序题目：技术面优先岗位专属题，其次类别题，最后通用专业题。"""
    direction = normalize_direction(direction)
    if role in ("hr", "behavioral"):
        return [q for q in QUESTIONS if q.type == role]
    scored = [(q, _matches_position(q, direction)) for q in QUESTIONS if q.type == "technical"]
    specific = [q for q, s in scored if s == 2]
    category = [q for q, s in scored if s == 1]
    general = [q for q in QUESTIONS if q.type == "technical" and q.category == "general"]
    if direction.startswith(CUSTOM_PREFIX) or not (specific or category):
        return general
    return [general[0], *specific, *category, *general[1:]]


def guided_question(direction: str, role: str, index: int) -> str:
    pool = questions_for_interview(direction, role)
    q = pool[index % len(pool)]
    return f"**第 {index + 1} 题**（{TYPES[q.type]} · {DIFFICULTIES[q.difficulty]}）\n\n{q.title}\n\n> 作答提示：{q.answer_outline}"
