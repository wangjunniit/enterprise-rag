#!/usr/bin/env python3
"""
企业RAG应用启动脚本
"""
import sys
from pathlib import Path

import uvicorn

# 修复Windows上的asyncio连接重置错误

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config import APP_HOST, APP_PORT, DEBUG

if __name__ == "__main__":
    print("🚀 启动企业RAG知识库应用...")
    print(f"📍 访问地址: http://{APP_HOST}:{APP_PORT}")
    print(f"📖 API文档: http://{APP_HOST}:{APP_PORT}/docs")
    print(f"🔧 调试模式: {'开启' if DEBUG else '关闭'}")
    
    uvicorn.run(
        "main:app",
        host=APP_HOST,
        port=APP_PORT,
        reload=DEBUG,
        log_level="info" if not DEBUG else "debug"
    )