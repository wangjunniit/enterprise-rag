#!/usr/bin/env python3
"""
数据库初始化脚本
"""
import logging
import os
import sys
from pathlib import Path

# 设置环境变量强制使用UTF-8编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PGCLIENTENCODING'] = 'UTF8'

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from db import init_db
from config import PG_URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """初始化数据库"""
    try:
        logger.info("开始初始化数据库...")
        logger.info(f"数据库连接: {PG_URL}")
        
        # 初始化数据库
        init_db()
        
        logger.info("✅ 数据库初始化完成！")
        logger.info("📋 创建的表:")
        logger.info("  - documents_chunk (文档分块表)")
        logger.info("📊 创建的索引:")
        logger.info("  - idx_document_version (文档ID和版本复合索引)")
        logger.info("  - idx_created_at (创建时间索引)")
        logger.info("  - idx_embedding_cosine (向量余弦相似度索引)")
        
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()