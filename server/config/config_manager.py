"""
配置管理器 - 提供便捷的配置访问接口

这是一个轻量级的配置管理器，依赖 Settings 类进行实际的配置加载
"""

from typing import Any, Optional
from .settings import settings


class ConfigManager:
    """
    配置管理器 - 统一管理配置的访问和修改
    
    使用单例模式，确保全局只有一个配置管理器实例
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键名
            default: 默认值
        
        Returns:
            配置值
        """
        return getattr(settings, key, default)
    
    def set(self, key: str, value: Any):
        """
        设置配置值（运行时修改）
        
        Args:
            key: 配置键名
            value: 配置值
        """
        if hasattr(settings, key):
            setattr(settings, key, value)
    
    def get_all(self) -> dict:
        """获取所有配置项"""
        return settings.to_dict()
    
    def validate(self) -> list:
        """验证配置的有效性"""
        return settings.validate()


# 全局配置管理器实例
config_manager = ConfigManager()


# 便捷函数
def get_config(key: str, default: Any = None) -> Any:
    """
    获取配置值（便捷函数）
    
    Args:
        key: 配置键名
        default: 默认值
    
    Returns:
        配置值
    """
    return config_manager.get(key, default)


def set_config(key: str, value: Any):
    """
    设置配置值（便捷函数）
    
    Args:
        key: 配置键名
        value: 配置值
    """
    config_manager.set(key, value)


def generate_env_template() -> str:
    """
    生成环境变量配置模板
    
    Returns:
        .env 文件内容
    """
    template = """# ============================================
# 基础配置
# ============================================
DEBUG=false
LOG_LEVEL=INFO
SERVICE_NAME=graphrag-api

# ============================================
# 数据库配置
# ============================================
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
REDIS_URL=redis://localhost:6379/0

# ============================================
# AI 配置
# ============================================
AI_PROVIDER=mock
AI_API_KEY=
AI_MODEL=qwen-max
AI_BASE_URL=
AI_TEMPERATURE=0.3
AI_MAX_TOKENS=4096

# ============================================
# 嵌入模型配置
# ============================================
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_DIMENSION=1536
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=

# ============================================
# FAISS 配置
# ============================================
FAISS_ENABLED=true
FAISS_INDEX_TYPE=hnsw
FAISS_INDEX_PATH=./data/faiss/index
FAISS_SEARCH_TOP_K=10
FAISS_SEARCH_THRESHOLD=0.7

# ============================================
# GraphRAG 配置
# ============================================
GRAPHRAG_ENABLED=true
GRAPHRAG_MAX_HOP=2
GRAPHRAG_THEME_WEIGHT=0.4
GRAPHRAG_VECTOR_WEIGHT=0.3
GRAPHRAG_KEYWORD_WEIGHT=0.2
GRAPHRAG_GRAPH_WEIGHT=0.1
"""
    return template