"""
实例注册表 - 管理全局单例实例

提供统一的方式来注册和获取全局服务实例，避免重复初始化。

使用方式：
    from config import instance_registry, get_instance, register_instance
    
    # 注册实例
    register_instance("my_service", MyService())
    
    # 获取实例
    my_service = get_instance("my_service")
"""

import logging
from typing import Any, Optional, Callable

logger = logging.getLogger("config.instances")


class InstanceRegistry:
    """
    实例注册表 - 管理全局单例实例
    
    使用单例模式，确保全局只有一个实例注册表
    """
    
    _instance = None
    _registry = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._registry = {}
        return cls._instance
    
    def register(self, name: str, instance: Any):
        """
        注册实例
        
        Args:
            name: 实例名称（用于标识）
            instance: 实例对象
        """
        if name in self._registry:
            logger.warning(f"Instance '{name}' already registered, replacing")
        
        self._registry[name] = instance
        logger.debug(f"Registered instance: {name}")
    
    def get(self, name: str) -> Optional[Any]:
        """
        获取实例
        
        Args:
            name: 实例名称
        
        Returns:
            实例对象或 None
        """
        return self._registry.get(name)
    
    def create_or_get(self, name: str, creator: Callable[..., Any], *args, **kwargs) -> Any:
        """
        获取或创建实例（单例模式）
        
        如果实例已存在，返回现有实例；否则使用 creator 函数创建新实例。
        
        Args:
            name: 实例名称
            creator: 创建实例的函数
            *args: 创建参数
            **kwargs: 创建关键字参数
        
        Returns:
            实例对象
        """
        if name not in self._registry:
            logger.info(f"Creating new instance: {name}")
            instance = creator(*args, **kwargs)
            self._registry[name] = instance
        else:
            logger.debug(f"Using existing instance: {name}")
        
        return self._registry[name]
    
    def exists(self, name: str) -> bool:
        """
        检查实例是否已注册
        
        Args:
            name: 实例名称
        
        Returns:
            是否存在
        """
        return name in self._registry
    
    def unregister(self, name: str):
        """
        注销实例
        
        Args:
            name: 实例名称
        """
        if name in self._registry:
            del self._registry[name]
            logger.debug(f"Unregistered instance: {name}")
    
    def clear(self):
        """清除所有已注册的实例"""
        self._registry = {}
        logger.info("Cleared all registered instances")
    
    def get_all_names(self) -> list:
        """获取所有已注册实例的名称"""
        return list(self._registry.keys())
    
    def get_count(self) -> int:
        """获取已注册实例的数量"""
        return len(self._registry)


# 全局实例注册表
instance_registry = InstanceRegistry()


# 便捷函数
def get_instance(name: str) -> Optional[Any]:
    """
    获取实例（便捷函数）
    
    Args:
        name: 实例名称
    
    Returns:
        实例对象或 None
    """
    return instance_registry.get(name)


def register_instance(name: str, instance: Any):
    """
    注册实例（便捷函数）
    
    Args:
        name: 实例名称
        instance: 实例对象
    """
    instance_registry.register(name, instance)


def create_or_get_instance(name: str, creator: Callable[..., Any], *args, **kwargs) -> Any:
    """
    获取或创建实例（便捷函数）
    
    Args:
        name: 实例名称
        creator: 创建实例的函数
        *args: 创建参数
        **kwargs: 创建关键字参数
    
    Returns:
        实例对象
    """
    return instance_registry.create_or_get(name, creator, *args, **kwargs)


# ============================================
# 预定义的实例名称常量
# ============================================

class InstanceNames:
    """预定义的实例名称"""
    
    NEO4J_CLIENT = "neo4j_client"
    FAISS_STORE = "faiss_store"
    REDIS_CLIENT = "redis_client"
    QA_SERVICE = "qa_service"
    GRAPH_SERVICE = "graph_service"
    QUERY_SERVICE = "query_service"
    CONFIG_SERVICE = "config_service"
    FAISS_INITIALIZER = "faiss_initializer"
    STORAGE = "storage"
    TRIPLET_EXTRACTOR = "triplet_extractor"
    ENTITY_LINKER = "entity_linker"
    AI_SEGMENTER = "ai_segmenter"


# ============================================
# 集中实例注册（延迟加载）
# ============================================

def initialize_instances():
    """
    初始化所有全局实例
    
    在此集中注册所有单例实例，确保：
    1. 所有实例在统一位置管理
    2. 避免循环导入问题（使用延迟加载）
    3. 便于测试时进行依赖注入
    """
    logger.info("Initializing global instances...")
    
    # Neo4j客户端（使用已存在的全局实例）
    from infra.neo4j_client import neo4j_client
    register_instance(InstanceNames.NEO4J_CLIENT, neo4j_client)
    
    # FAISS向量存储（使用已存在的全局实例，避免重复创建）
    from infra.faiss_store import faiss_store
    if faiss_store is None:
        from infra.faiss_store import FaissStore
        faiss_store = FaissStore()
    register_instance(InstanceNames.FAISS_STORE, faiss_store)
    
    # Redis客户端
    try:
        from infra.redis_client import RedisClient
        redis_client = RedisClient()
        register_instance(InstanceNames.REDIS_CLIENT, redis_client)
    except ImportError:
        logger.warning("Redis client not available, skipping registration")
    
    # 配置服务
    from services.config_service import ConfigService
    config_service = ConfigService()
    register_instance(InstanceNames.CONFIG_SERVICE, config_service)
    
    # QA服务（使用已存在的全局实例）
    from services.qa_service import qa_service
    register_instance(InstanceNames.QA_SERVICE, qa_service)
    
    # 图服务
    from services.graph_service import GraphService
    graph_service = GraphService()
    register_instance(InstanceNames.GRAPH_SERVICE, graph_service)
    
    # 查询服务
    from graphrag.stages.stage7_query_service import QueryService
    query_service = QueryService()
    register_instance(InstanceNames.QUERY_SERVICE, query_service)
    
    # 存储服务
    from infra.storage import Storage
    storage = Storage()
    register_instance(InstanceNames.STORAGE, storage)
    
    # 三元组提取器
    from services.extractor import TripletExtractor
    extractor = TripletExtractor()
    register_instance(InstanceNames.TRIPLET_EXTRACTOR, extractor)
    
    # 实体链接器
    from services.linker import EntityLinker
    linker = EntityLinker()
    register_instance(InstanceNames.ENTITY_LINKER, linker)
    
    # AI分词器
    try:
        from services.ai_segmenter import AISegmenter
        ai_segmenter = AISegmenter()
        register_instance(InstanceNames.AI_SEGMENTER, ai_segmenter)
    except ValueError:
        logger.warning("AI segmenter not available, skipping registration")
    
    logger.info(f"Successfully registered {instance_registry.get_count()} instances")