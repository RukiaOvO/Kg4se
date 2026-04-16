"""
配置类定义 - 所有配置项的类型定义和默认值

配置优先级：
1. 环境变量（最高优先级）
2. 默认值（后备）
"""

import os
from typing import Optional, Literal, List, Dict, Any
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    项目配置类
    
    所有配置项都从环境变量读取，提供合理的默认值
    """
    
    # ============================================
    # 基础配置
    # ============================================
    
    debug_mode: bool = False
    log_level: str = "INFO"
    service_name: str = "graphrag-api"
    
    # ============================================
    # 数据库配置
    # ============================================
    
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j1234"
    
    redis_url: str = "redis://localhost:6379/0"
    
    # ============================================
    # AI 配置
    # ============================================
    
    ai_provider: Literal[
        "openai", "anthropic", "google", "grok", "deepseek",
        "qwen", "glm", "moonshot", "ernie", "minimax", "doubao",
        "ollama", "nvidia", "modelscope", "zhizengzeng", "mock"
    ] = "mock"
    
    ai_api_key: Optional[str] = None
    ai_model: Optional[str] = None
    ai_base_url: Optional[str] = None
    ai_temperature: float = 0.3
    ai_max_tokens: int = 4096
    
    # ============================================
    # 嵌入模型配置
    # ============================================
    
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
    embedding_dimension: int = int(os.getenv("EMBEDDING_DIMENSION", "1536"))
    embedding_api_key: Optional[str] = None
    embedding_base_url: Optional[str] = None
    
    # ============================================
    # FAISS 配置
    # ============================================
    
    faiss_enabled: bool = True
    faiss_index_type: Literal["hnsw", "ivf", "flat", "pq"] = "hnsw"
    faiss_index_path: str = "./data/faiss/index"
    faiss_search_top_k: int = 10
    faiss_search_threshold: float = 0.7
    
    # ============================================
    # GraphRAG 配置
    # ============================================
    
    graphrag_enabled: bool = True
    graphrag_max_hop: int = 2
    graphrag_theme_weight: float = 0.4
    graphrag_vector_weight: float = 0.3
    graphrag_keyword_weight: float = 0.2
    graphrag_graph_weight: float = 0.1
    
    # ============================================
    # API 配置
    # ============================================
    
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    upload_dir: str = "./uploads"
    
    # ============================================
    # GraphRAG 功能开关 (v2.0)
    # ============================================
    
    enable_neo4j_graphrag: bool = True
    enable_vector_search: bool = True
    
    # ============================================
    # 模型配置
    # ============================================
    
    llm_model: str = "qwen-plus"
    
    # ============================================
    # 本体约束配置
    # ============================================
    
    allowed_node_types: List[str] = [
        "Concept", "Person", "Method", "Tool", "Metric",
        "Chunk", "Claim", "Theme", "Document", "Topic"
    ]
    
    allowed_relations: List[str] = [
        "IS_A", "PART_OF", "USES", "IMPLEMENTED_BY", "CREATES",
        "DERIVES_FROM", "CONTAINS", "BELONGS_TO", "SUPPORTS",
        "CONTRADICTS", "CAUSES", "COMPARES_WITH", "CONDITIONS",
        "PURPOSE", "MENTIONS", "CONTAINS_CLAIM", "BELONGS_TO_THEME",
        "EVIDENCE_FROM", "SIMILAR_TO"
    ]
    
    # ============================================
    # 阈值配置
    # ============================================
    
    entity_link_accept_threshold: float = 0.85
    entity_link_review_threshold: float = 0.65
    claim_confidence_threshold: float = 0.7
    
    vector_search_top_k: int = 5
    vector_search_threshold: float = 0.7
    
    # ============================================
    # 社区检测配置
    # ============================================
    
    community_algorithm: str = "louvain"
    community_min_size: int = 3
    
    # ============================================
    # 谓词治理配置
    # ============================================
    
    predicate_governance_enabled: bool = True
    predicate_mapping_file: str = "graphrag/config/predicates.yaml"
    ontology_config_file: str = "graphrag/config/ontology.yaml"
    
    # ============================================
    # 构建版本配置
    # ============================================
    
    build_version_prefix: str = "v2.0"
    
    # ============================================
    # 兼容性配置（旧版本）
    # ============================================
    
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: Optional[str] = None
    
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    
    class Config:
        """Pydantic 配置"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
    
    @classmethod
    def from_env(cls):
        """从环境变量加载配置"""
        return cls(
            # 基础配置
            debug_mode=cls._get_bool("DEBUG", False),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            service_name=os.getenv("SERVICE_NAME", "graphrag-api"),
            
            # 数据库配置
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "neo4j1234"),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            
            # AI 配置
            ai_provider=os.getenv("AI_PROVIDER", "mock"),
            ai_api_key=os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY"),
            ai_model=os.getenv("AI_MODEL"),
            ai_base_url=os.getenv("AI_BASE_URL") or os.getenv("OPENAI_BASE_URL"),
            ai_temperature=float(os.getenv("AI_TEMPERATURE", "0.3")),
            ai_max_tokens=int(os.getenv("AI_MAX_TOKENS", "4096")),
            
            # 嵌入模型配置
            embedding_model=os.getenv("EMBEDDING_MODEL", "text-embedding-v3"),
            embedding_dimension=int(os.getenv("EMBEDDING_DIMENSION", "1536")),
            embedding_api_key=os.getenv("EMBEDDING_API_KEY") or os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY"),
            embedding_base_url=os.getenv("EMBEDDING_BASE_URL") or os.getenv("AI_BASE_URL") or os.getenv("OPENAI_BASE_URL"),
            
            # FAISS 配置
            faiss_enabled=cls._get_bool("FAISS_ENABLED", True),
            faiss_index_type=os.getenv("FAISS_INDEX_TYPE", "hnsw"),
            faiss_index_path=os.getenv("FAISS_INDEX_PATH", "./data/faiss/index"),
            faiss_search_top_k=int(os.getenv("FAISS_SEARCH_TOP_K", "10")),
            faiss_search_threshold=float(os.getenv("FAISS_SEARCH_THRESHOLD", "0.7")),
            
            # GraphRAG 配置
            graphrag_enabled=cls._get_bool("GRAPHRAG_ENABLED", True),
            graphrag_max_hop=int(os.getenv("GRAPHRAG_MAX_HOP", "2")),
            graphrag_theme_weight=float(os.getenv("GRAPHRAG_THEME_WEIGHT", "0.4")),
            graphrag_vector_weight=float(os.getenv("GRAPHRAG_VECTOR_WEIGHT", "0.3")),
            graphrag_keyword_weight=float(os.getenv("GRAPHRAG_KEYWORD_WEIGHT", "0.2")),
            graphrag_graph_weight=float(os.getenv("GRAPHRAG_GRAPH_WEIGHT", "0.1")),
            
            # API 配置
            api_host=os.getenv("API_HOST", "0.0.0.0"),
            api_port=int(os.getenv("API_PORT", "8000")),
            upload_dir=os.getenv("UPLOAD_DIR", "./uploads"),
            
            # GraphRAG 功能开关
            enable_neo4j_graphrag=cls._get_bool("ENABLE_NEO4J_GRAPHRAG", True),
            enable_vector_search=cls._get_bool("ENABLE_VECTOR_SEARCH", True),
            
            # 模型配置
            llm_model=os.getenv("LLM_MODEL", "qwen-plus"),
            
            # 阈值配置
            entity_link_accept_threshold=float(os.getenv("ENTITY_LINK_ACCEPT_THRESHOLD", "0.85")),
            entity_link_review_threshold=float(os.getenv("ENTITY_LINK_REVIEW_THRESHOLD", "0.65")),
            claim_confidence_threshold=float(os.getenv("CLAIM_CONFIDENCE_THRESHOLD", "0.7")),
            vector_search_top_k=int(os.getenv("VECTOR_SEARCH_TOP_K", "5")),
            vector_search_threshold=float(os.getenv("VECTOR_SEARCH_THRESHOLD", "0.7")),
            
            # 社区检测配置
            community_algorithm=os.getenv("COMMUNITY_ALGORITHM", "louvain"),
            community_min_size=int(os.getenv("COMMUNITY_MIN_SIZE", "3")),
            
            # 谓词治理配置
            predicate_governance_enabled=cls._get_bool("PREDICATE_GOVERNANCE_ENABLED", True),
            predicate_mapping_file=os.getenv("PREDICATE_MAPPING_FILE", "graphrag/config/predicates.yaml"),
            ontology_config_file=os.getenv("ONTOLOGY_CONFIG_FILE", "graphrag/config/ontology.yaml"),
            
            # 构建版本配置
            build_version_prefix=os.getenv("BUILD_VERSION_PREFIX", "v2.0"),
            
            # 兼容性配置（旧版本）
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            openai_base_url=os.getenv("OPENAI_BASE_URL"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3")
        )
    
    @staticmethod
    def _get_bool(key: str, default: bool = False) -> bool:
        """获取布尔类型环境变量"""
        value = os.getenv(key)
        if value is None:
            return default
        return value.lower() in ("true", "1", "yes", "on")
    
    def validate(self) -> List[str]:
        """
        验证配置的有效性
        
        Returns:
            错误消息列表（如果验证通过则为空）
        """
        errors = []
        
        # 验证 AI 配置
        if self.ai_provider != "mock" and not self.ai_api_key:
            errors.append("AI_API_KEY is required when AI_PROVIDER is not 'mock'")
        
        # 验证嵌入配置
        valid_embedding_models = [
            "text-embedding-3-small",
            "text-embedding-3-large",
            "text-embedding-ada-002",
            "text-embedding-v3",
            "all-MiniLM-L6-v2",
            "bge-large-en",
            "bge-base-en"
        ]
        if self.embedding_model not in valid_embedding_models:
            errors.append(f"Unknown embedding model: {self.embedding_model}")
        
        # 验证 FAISS 索引类型
        valid_index_types = ["hnsw", "ivf", "flat", "pq"]
        if self.faiss_index_type not in valid_index_types:
            errors.append(f"Unknown FAISS index type: {self.faiss_index_type}")
        
        # 验证 AI 提供商
        valid_providers = [
            "openai", "anthropic", "google", "grok", "deepseek",
            "qwen", "glm", "moonshot", "ernie", "minimax", "doubao",
            "ollama", "nvidia", "modelscope", "zhizengzeng", "mock"
        ]
        if self.ai_provider not in valid_providers:
            errors.append(f"Unknown AI provider: {self.ai_provider}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {k: v for k, v in self.dict().items() if not k.startswith("_")}


# 全局配置实例
settings = Settings.from_env()