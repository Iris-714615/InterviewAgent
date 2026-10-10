"""应用配置 - 多模型动态路由,省钱省 token"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    # ============ 网关(共用)============
    api_key: str = "sk-your-api-key"
    base_url: str = "https://tokendance.space/gateway/v1"

    # ============ 对话模型(按复杂度路由)============
    # 简单问答 → flash(最省钱)
    model_flash: str = "deepseek-v4-flash"
    # 常规面试对话/辅导 → pro(平衡)
    model_pro: str = "deepseek-v4-pro"
    # 复杂评估/深度分析 → glm(最强)
    model_glm: str = "glm-5.2"

    # ============ Embedding 向量模型 ============
    embedding_model: str = "qwen-text-embedding-v4"
    embedding_api_key: str = ""
    embedding_base_url: str = ""
    embedding_timeout_seconds: float = 3.0
    rag_timeout_seconds: float = 4.0
    rag_vector_enabled: bool = False
    llm_timeout_seconds: float = 15.0
    chat_first_token_seconds: float = 12.0
    chat_idle_seconds: float = 10.0
    chat_total_seconds: float = 45.0
    chat_max_tokens: int = 600
    live_profile_enabled: bool = False
    tts_timeout_seconds: float = 6.0

    # ============ TTS 语音模型 ============
    # mimo-v2.5-tts 预置音色(中文男声):冰糖/茉莉(女) 苏打/白桦(男)
    tts_model: str = "mimo-v2.5-tts"
    tts_voice: str = "苏打"  # 中文男声,面试官场景

    # ============ ASR 语音识别模型 ============
    # provider: "local" 用本地 faster-whisper(免费,默认)
    #          "api" 用 OpenAI 兼容 transcriptions 接口
    asr_provider: str = "local"
    # 本地模式:模型大小(tiny/base/small/medium/large-v3)
    # 中文准确率优先 medium(769MB),速度优先 small(244MB)
    asr_model: str = "medium"
    # 本地模式:设备(cpu 或 cuda)
    asr_device: str = "cpu"
    # API 模式:端点(留空则复用 base_url)
    asr_base_url: str = ""
    asr_api_key: str = ""  # 留空则复用 api_key
    # 识别语言提示(留空自动检测,填 "zh" 强制中文)
    asr_language: str = "zh"

    # ============ 应用 ============
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = True
    demo_mode: bool = False

    # ============ 数据库 ============
    database_url: str = "sqlite+aiosqlite:///./data/interview.db"

    # ============ 向量库 ============
    chroma_persist_dir: str = "./data/chroma"

    # ============ 上传与隐私 ============
    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 20
    default_retention_days: int = 30
    pii_redaction_enabled: bool = True

    # 每百万 token 估算成本（同一计价单位）
    cost_flash_input_per_million: float = 0.2
    cost_flash_output_per_million: float = 0.8
    cost_pro_input_per_million: float = 1.0
    cost_pro_output_per_million: float = 4.0
    cost_glm_input_per_million: float = 2.0
    cost_glm_output_per_million: float = 8.0

    # ============ CORS ============
    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def chroma_path(self) -> Path:
        p = Path(self.chroma_persist_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
