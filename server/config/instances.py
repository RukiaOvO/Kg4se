"""
实例注册表 - 管理全局单例实例

提供统一的方式来注册和获取全局服务实例，避免重复初始化。

特性：
1. 支持延迟初始化（解决循环依赖问题）
2. 单例模式确保全局唯一实例
3. 支持工厂函数注册
4. 提供便捷的注册和获取接口

使用方式：
    from config import instance_registry, get_instance, register_instance
    
    # 注册实例
    register_instance("my_service", MyService())
    
    # 获取实例
    my_service = get_instance("my_service")
    
    # 延迟注册（推荐用于解决循环依赖）
    register_factory("my_service", MyService)
    my_service = get_instance("my_service")  # 此时才真正创建实例
"""

import logging
from typing import Any, Optional, Callable, Dict, Union

logger = logging.getLogger("config.instances")


class InstanceRegistry:
    """
    实例注册表 - 管理全局单例实例
    
    使用单例模式，确保全局只有一个实例注册表
    
    延迟初始化机制：
    - 支持注册工厂函数（callable）而不是直接注册实例
    - 当首次调用 get() 时，如果存储的是工厂函数，则调用它创建实例
    - 创建后的实例会被缓存，后续调用直接返回缓存的实例
    """
    
    _instance = None
    _registry: Dict[str, Union[Any, Callable[..., Any]]] = {}
    _initialized: Dict[str, bool] = {}  # 跟踪哪些实例已经被初始化
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._registry = {}
            cls._initialized = {}
        return cls._instance
    
    def register(self, name: str, instance: Any):
        """
        注册实例（直接注册，立即创建）
        
        Args:
            name: 实例名称（用于标识）
            instance: 实例对象
        """
        if name in self._registry:
            logger.warning(f"Instance '{name}' already registered, replacing")
        
        self._registry[name] = instance
        self._initialized[name] = True
        logger.debug(f"Registered instance: {name}")
    
    def register_factory(self, name: str, factory: Callable[..., Any], *args, **kwargs):
        """
        注册工厂函数（延迟初始化）
        
        当首次调用 get() 时，会调用 factory(*args, **kwargs) 创建实例
        
        Args:
            name: 实例名称
            factory: 创建实例的工厂函数（类或函数）
            *args: 传递给工厂函数的位置参数
            **kwargs: 传递给工厂函数的关键字参数
        """
        if name in self._registry:
            logger.warning(f"Factory '{name}' already registered, replacing")
        
        # 存储工厂函数及其参数
        self._registry[name] = (factory, args, kwargs)
        self._initialized[name] = False
        logger.debug(f"Registered factory for instance: {name}")
    
    def get(self, name: str) -> Optional[Any]:
        """
        获取实例（支持延迟初始化）
        
        如果注册的是工厂函数，则首次调用时创建实例并缓存
        
        Args:
            name: 实例名称
        
        Returns:
            实例对象或 None
        """
        if name not in self._registry:
            logger.debug(f"Instance '{name}' not found in registry")
            return None
        
        # 如果是工厂函数，需要先创建实例
        if not self._initialized.get(name, False):
            factory_info = self._registry[name]
            if isinstance(factory_info, tuple) and len(factory_info) >= 1:
                factory, args, kwargs = factory_info if len(factory_info) == 3 else (factory_info[0], (), {})
                try:
                    logger.info(f"Initializing instance '{name}' using factory...")
                    instance = factory(*args, **kwargs)
                    self._registry[name] = instance
                    self._initialized[name] = True
                    logger.info(f"Successfully initialized instance: {name}")
                except Exception as e:
                    logger.error(f"Failed to initialize instance '{name}': {e}")
                    return None
        
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
            self._initialized[name] = True
        else:
            logger.debug(f"Using existing instance: {name}")
        
        return self._registry[name]
    
    def exists(self, name: str) -> bool:
        """
        检查实例是否已注册（包括未初始化的工厂）
        
        Args:
            name: 实例名称
        
        Returns:
            是否存在
        """
        return name in self._registry
    
    def is_initialized(self, name: str) -> bool:
        """
        检查实例是否已被初始化
        
        Args:
            name: 实例名称
        
        Returns:
            是否已初始化
        """
        return self._initialized.get(name, False)
    
    def unregister(self, name: str):
        """
        注销实例
        
        Args:
            name: 实例名称
        """
        if name in self._registry:
            del self._registry[name]
            if name in self._initialized:
                del self._initialized[name]
            logger.debug(f"Unregistered instance: {name}")
    
    def clear(self):
        """清除所有已注册的实例"""
        self._registry = {}
        self._initialized = {}
        logger.info("Cleared all registered instances")
    
    def get_all_names(self) -> list:
        """获取所有已注册实例的名称"""
        return list(self._registry.keys())
    
    def get_count(self) -> int:
        """获取已注册实例的数量"""
        return len(self._registry)
    
    def get_initialized_count(self) -> int:
        """获取已初始化实例的数量"""
        return sum(1 for initialized in self._initialized.values() if initialized)
    
    def shutdown(self):
        """
        优雅地关闭所有实例
        
        调用实例的 close() 或 shutdown() 方法（如果存在）
        """
        logger.info("Shutting down all instances...")
        
        for name, instance in list(self._registry.items()):
            if self._initialized.get(name, False) and hasattr(instance, 'close'):
                try:
                    instance.close()
                    logger.debug(f"Closed instance: {name}")
                except Exception as e:
                    logger.error(f"Failed to close instance '{name}': {e}")
        
        self.clear()


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


def register_factory(name: str, factory: Callable[..., Any], *args, **kwargs):
    """
    注册工厂函数（便捷函数，延迟初始化）
    
    Args:
        name: 实例名称
        factory: 创建实例的工厂函数（类或函数）
        *args: 传递给工厂函数的位置参数
        **kwargs: 传递给工厂函数的关键字参数
    """
    instance_registry.register_factory(name, factory, *args, **kwargs)


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
# 集中实例注册（支持延迟加载）
# ============================================

def initialize_instances():
    """
    初始化所有全局实例
    
    在此集中注册所有单例实例，确保：
    1. 所有实例在统一位置管理
    2. 使用延迟加载避免循环导入问题
    3. 便于测试时进行依赖注入
    
    使用 register_factory() 注册的实例会在首次 get() 时才真正创建
    """
    logger.info("Initializing global instances...")
    
    # Neo4j客户端（使用工厂模式延迟初始化）
    register_factory(InstanceNames.NEO4J_CLIENT, _create_neo4j_client)
    
    # FAISS向量存储（使用工厂模式延迟初始化）
    register_factory(InstanceNames.FAISS_STORE, _create_faiss_store)
    
    # Redis客户端（使用工厂模式延迟初始化）
    register_factory(InstanceNames.REDIS_CLIENT, _create_redis_client)
    
    # 配置服务（使用工厂模式延迟初始化）
    register_factory(InstanceNames.CONFIG_SERVICE, _create_config_service)
    
    # QA服务（使用工厂模式延迟初始化）
    register_factory(InstanceNames.QA_SERVICE, _create_qa_service)
    
    # 图服务（使用工厂模式延迟初始化）
    register_factory(InstanceNames.GRAPH_SERVICE, _create_graph_service)
    
    # 查询服务（使用工厂模式延迟初始化）
    register_factory(InstanceNames.QUERY_SERVICE, _create_query_service)
    
    # 存储服务（使用工厂模式延迟初始化）
    register_factory(InstanceNames.STORAGE, _create_storage)
    
    # 三元组提取器（使用工厂模式延迟初始化）
    register_factory(InstanceNames.TRIPLET_EXTRACTOR, _create_triplet_extractor)
    
    # 实体链接器（使用工厂模式延迟初始化）
    register_factory(InstanceNames.ENTITY_LINKER, _create_entity_linker)
    
    # AI分词器（使用工厂模式延迟初始化）
    register_factory(InstanceNames.AI_SEGMENTER, _create_ai_segmenter)
    
    logger.info(f"Registered {instance_registry.get_count()} factories (delayed initialization)")


# ============================================
# 工厂函数（延迟初始化时调用）
# ============================================

def _create_neo4j_client():
    """创建 Neo4j 客户端实例"""
    from infra.neo4j_client import neo4j_client
    return neo4j_client


def _create_faiss_store():
    """创建 FAISS 存储实例"""
    from infra.faiss_store import faiss_store
    if faiss_store is None:
        from infra.faiss_store import FaissStore
        return FaissStore()
    return faiss_store


def _create_redis_client():
    """创建 Redis 客户端实例"""
    try:
        from infra.redis_client import RedisClient
        return RedisClient()
    except ImportError as e:
        logger.warning(f"Redis client not available: {e}")
        return None


def _create_config_service():
    """创建配置服务实例"""
    from services.config_service import ConfigService
    return ConfigService()


def _create_qa_service():
    """创建 QA 服务实例"""
    from services.qa_service import qa_service
    return qa_service


def _create_graph_service():
    """创建图服务实例"""
    from services.graph_service import GraphService
    return GraphService()


def _create_query_service():
    """创建查询服务实例"""
    from graphrag.stages.stage7_query_service import QueryService
    return QueryService()


def _create_storage():
    """创建存储服务实例"""
    from infra.storage import Storage
    return Storage()


def _create_triplet_extractor():
    """创建三元组提取器实例"""
    from services.extractor import TripletExtractor
    return TripletExtractor()


def _create_entity_linker():
    """创建实体链接器实例"""
    from services.linker import EntityLinker
    return EntityLinker()


def _create_ai_segmenter():
    """创建 AI 分词器实例"""
    try:
        from services.ai_segmenter import AISegmenter
        return AISegmenter()
    except ValueError as e:
        logger.warning(f"AI segmenter not available: {e}")
        return None