"""
配置模块 - 统一管理项目配置和全局实例

使用方式：
    from config import settings, config_manager, get_config, get_instance
    
    # 获取配置
    model = settings.embedding_model
    
    # 获取全局实例
    faiss_store = get_instance("faiss_store")
"""

from .settings import Settings, settings
from .config_manager import ConfigManager, config_manager, get_config, set_config
from .instances import InstanceRegistry, instance_registry, get_instance, register_instance, InstanceNames, initialize_instances

__all__ = [
    "Settings",
    "settings",
    "ConfigManager",
    "config_manager",
    "get_config",
    "set_config",
    "InstanceRegistry",
    "instance_registry",
    "get_instance",
    "register_instance",
    "InstanceNames",
    "initialize_instances"
]