"""
基础设施层配置模块 - 从统一配置源导入设置

注意：此文件仅用于向后兼容，所有配置项已迁移到 config/settings.py
"""

# 从统一配置源导入 Settings 类和全局实例
from config import Settings, settings

# 保持向后兼容性的别名
__all__ = ["Settings", "settings"]
