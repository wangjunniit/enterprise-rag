import logging
import os
import time
from functools import wraps
from typing import Any, Callable
from config import LOG_LEVEL

def setup_logging():
    """配置日志系统"""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('rag_app.log', encoding='utf-8')
        ]
    )

def timer(func: Callable) -> Callable:
    """计时装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        logging.getLogger(func.__module__).info(
            f"{func.__name__} 执行时间: {end_time - start_time:.2f}秒"
        )
        return result
    return wrapper

def validate_file_size(file_path: str, max_size_mb: int = 100) -> bool:
    """验证文件大小"""
    try:
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        return size_mb <= max_size_mb
    except OSError:
        return False

def safe_execute(func: Callable, *args, **kwargs) -> tuple[bool, Any]:
    """安全执行函数，返回(成功标志, 结果或错误信息)"""
    try:
        result = func(*args, **kwargs)
        return True, result
    except Exception as e:
        logging.getLogger(__name__).error(f"执行失败 {func.__name__}: {e}")
        return False, str(e)

def batch_process(items: list, batch_size: int = None, process_func: Callable = None):
    """批量处理数据"""
    if batch_size is None:
        from config import BATCH_COMMIT_SIZE
        batch_size = BATCH_COMMIT_SIZE
    if not process_func:
        return items
    
    results = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = []
        for item in batch:
            success, result = safe_execute(process_func, item)
            if success:
                batch_results.append(result)
        results.extend(batch_results)
    
    return results

def format_file_size(size_bytes: int) -> str:
    """格式化文件大小显示"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def get_system_info():
    """获取系统信息"""
    import psutil
    import platform
    
    return {
        "platform": platform.system(),
        "platform_version": platform.version(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "cpu_count": psutil.cpu_count(),
        "memory_total": format_file_size(psutil.virtual_memory().total),
        "memory_available": format_file_size(psutil.virtual_memory().available),
        "disk_usage": format_file_size(psutil.disk_usage('/').total)
    }