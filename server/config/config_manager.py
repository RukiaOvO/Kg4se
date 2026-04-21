"""
配置管理器 - 提供便捷的配置访问接口

这是一个轻量级的配置管理器，依赖 Settings 类进行实际的配置加载

特性：
1. 支持运行时配置覆盖（不影响原始配置）
2. 统一的配置访问接口
3. 单例模式确保全局唯一实例
"""

from typing import Any, Optional, Dict
from .settings import settings


class ConfigManager:
    """
    配置管理器 - 统一管理配置的访问和修改
    
    使用单例模式，确保全局只有一个配置管理器实例
    
    运行时配置覆盖机制：
    - 通过 set_runtime() 设置的配置会覆盖原始配置
    - 运行时配置存储在内存中，重启后会丢失
    - 使用 clear_runtime() 可以清除所有运行时覆盖
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._runtime_config = {}  # 运行时配置覆盖
        return cls._instance
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        优先从运行时配置读取，回退到环境变量配置
        
        Args:
            key: 配置键名
            default: 默认值
        
        Returns:
            配置值
        """
        if key in self._runtime_config:
            return self._runtime_config[key]
        return getattr(settings, key, default)
    
    def set(self, key: str, value: Any):
        """
        设置配置值（直接修改原始配置，不推荐）
        
        注意：此方法会直接修改 settings 对象，建议使用 set_runtime()
        
        Args:
            key: 配置键名
            value: 配置值
        """
        if hasattr(settings, key):
            setattr(settings, key, value)
    
    def set_runtime(self, key: str, value: Any):
        """
        设置运行时配置（临时生效，重启后丢失）
        
        使用此方法设置的配置会覆盖原始配置，但不会持久化
        
        Args:
            key: 配置键名
            value: 配置值
        """
        self._runtime_config[key] = value
    
    def clear_runtime(self):
        """
        清空所有运行时配置覆盖
        
        调用后所有配置将恢复为原始值
        """
        self._runtime_config.clear()
    
    def is_runtime_override(self, key: str) -> bool:
        """
        检查指定配置是否被运行时覆盖
        
        Args:
            key: 配置键名
        
        Returns:
            是否被运行时覆盖
        """
        return key in self._runtime_config
    
    def get_runtime_keys(self) -> list:
        """
        获取所有被运行时覆盖的配置键名
        
        Returns:
            运行时配置键名列表
        """
        return list(self._runtime_config.keys())
    
    def get_all(self) -> dict:
        """
        获取所有配置项（包含运行时覆盖）
        
        Returns:
            所有配置项的字典
        """
        result = settings.to_dict()
        result.update(self._runtime_config)
        return result
    
    def get_all_with_origin(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有配置项及其来源信息
        
        Returns:
            包含配置值和来源的字典
            来源类型: 'env'（环境变量）、'default'（默认值）、'runtime'（运行时覆盖）
        """
        result = {}
        for key, value in settings.to_dict().items():
            if key in self._runtime_config:
                result[key] = {
                    "value": self._runtime_config[key],
                    "origin": "runtime"
                }
            elif hasattr(settings.__class__, key) and getattr(settings.__class__, key).default == value:
                result[key] = {
                    "value": value,
                    "origin": "default"
                }
            else:
                result[key] = {
                    "value": value,
                    "origin": "env"
                }
        return result
    
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
    设置配置值（便捷函数，直接修改原始配置）
    
    Args:
        key: 配置键名
        value: 配置值
    """
    config_manager.set(key, value)


def set_runtime_config(key: str, value: Any):
    """
    设置运行时配置（便捷函数，临时生效）
    
    Args:
        key: 配置键名
        value: 配置值
    """
    config_manager.set_runtime(key, value)


def clear_runtime_config():
    """清除所有运行时配置覆盖"""
    config_manager.clear_runtime()


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