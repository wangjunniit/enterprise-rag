"""
Windows asyncio连接重置错误修复模块
"""
import asyncio
import logging
import platform
import warnings
from typing import Any, Dict

def setup_windows_asyncio_fix():
    """设置Windows系统的asyncio修复"""
    if platform.system() != 'Windows':
        return
    
    # 1. 设置事件循环策略
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception as e:
        logging.warning(f"设置Windows事件循环策略失败: {e}")
    
    # 2. 忽略asyncio相关的警告和错误日志
    logging.getLogger('asyncio').setLevel(logging.CRITICAL)
    
    # 3. 忽略特定的警告
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="asyncio")
    
    # 4. 设置全局异常处理器
    def handle_exception(loop, context):
        """处理asyncio异常"""
        exception = context.get('exception')
        
        # 忽略连接重置相关的错误
        if isinstance(exception, (ConnectionResetError, ConnectionAbortedError, OSError)):
            error_code = getattr(exception, 'winerror', None) or getattr(exception, 'errno', None)
            # Windows错误代码：10054 = 连接被远程主机强制关闭
            if error_code in [10054, 10053, 10038]:
                return  # 静默忽略这些错误
        
        # 忽略管道相关的错误
        if 'pipe' in str(exception).lower() or 'transport' in str(exception).lower():
            return
            
        # 对于其他异常，使用默认处理
        if hasattr(loop, 'default_exception_handler'):
            loop.default_exception_handler(context)
        else:
            # 如果没有默认处理器，记录错误但不抛出
            logging.error(f"Asyncio异常: {context}")
    
    # 5. 应用异常处理器到当前事件循环
    try:
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(handle_exception)
    except RuntimeError:
        # 如果没有运行的事件循环，创建一个新的
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.set_exception_handler(handle_exception)
        except Exception as e:
            logging.warning(f"设置异常处理器失败: {e}")

def suppress_connection_errors():
    """抑制连接错误的日志输出"""
    # 创建一个自定义的日志过滤器
    class ConnectionErrorFilter(logging.Filter):
        def filter(self, record):
            # 过滤掉连接重置相关的错误消息
            message = record.getMessage().lower()
            error_keywords = [
                'connection reset',
                'connection aborted', 
                'remote host closed',
                'winerror 10054',
                'winerror 10053',
                '_call_connection_lost',
                'proactorbasepipetransport'
            ]
            
            for keyword in error_keywords:
                if keyword in message:
                    return False
            return True
    
    # 应用过滤器到相关的日志记录器
    loggers_to_filter = ['asyncio', 'uvicorn', 'uvicorn.error', 'fastapi']
    for logger_name in loggers_to_filter:
        logger = logging.getLogger(logger_name)
        logger.addFilter(ConnectionErrorFilter())

# 自动应用修复（当模块被导入时）
if platform.system() == 'Windows':
    setup_windows_asyncio_fix()
    suppress_connection_errors()