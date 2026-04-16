"""
统一日志模块 - 为整个应用提供标准化的日志管理

特点：
1. 统一配置所有日志输出格式
2. 支持控制台和文件双重输出
3. 根据环境配置不同的日志级别
4. 自动过滤第三方库的日志噪音
"""

import logging
import sys
from typing import Optional
from config import settings

# 全局日志配置
_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 存储已创建的 logger 实例，避免重复创建
_loggers = {}


def setup_logging():
    """
    初始化全局日志配置
    
    应在应用启动时调用此函数，确保所有模块使用统一的日志设置
    """
    # 获取配置的日志级别
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(_formatter)
    console_handler.setLevel(log_level)
    
    # 收集所有处理器
    handlers = [console_handler]
    
    # 如果不是调试模式，同时输出到文件
    if not settings.debug_mode:
        file_handler = logging.FileHandler("app.log", encoding="utf-8")
        file_handler.setFormatter(_formatter)
        file_handler.setLevel(log_level)
        handlers.append(file_handler)
    
    # 配置根 logger
    logging.basicConfig(
        level=log_level,
        handlers=handlers,
        force=True
    )
    
    # 设置第三方库的日志级别，减少噪音
    logging.getLogger("neo4j").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    
    # 记录初始化完成
    root_logger = logging.getLogger("app")
    root_logger.info(f"日志系统初始化完成，级别: {settings.log_level.upper()}")


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的 logger 实例
    
    Args:
        name: logger 名称，建议使用模块路径（如 "services.qa_service"）
    
    Returns:
        配置好的 logger 实例
    """
    if name not in _loggers:
        logger = logging.getLogger(name)
        _loggers[name] = logger
    
    return _loggers[name]


def log_method_call(logger: logging.Logger, method_name: str, **kwargs):
    """
    辅助函数：记录方法调用日志
    
    Args:
        logger: logger 实例
        method_name: 方法名称
        **kwargs: 方法参数
    """
    if logger.isEnabledFor(logging.DEBUG):
        params_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        logger.debug(f"调用方法: {method_name}({params_str})")


def log_method_result(logger: logging.Logger, method_name: str, result: Optional[any] = None, error: Optional[Exception] = None):
    """
    辅助函数：记录方法执行结果
    
    Args:
        logger: logger 实例
        method_name: 方法名称
        result: 方法返回值（成功时）
        error: 异常对象（失败时）
    """
    if error:
        logger.error(f"方法 {method_name} 执行失败: {error}")
    elif logger.isEnabledFor(logging.DEBUG):
        result_str = str(result)[:100] + "..." if result and len(str(result)) > 100 else str(result)
        logger.debug(f"方法 {method_name} 执行成功: {result_str}")


__all__ = ["setup_logging", "get_logger", "log_method_call", "log_method_result"]