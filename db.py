import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from config import PG_URL
from models import Base

logger = logging.getLogger(__name__)

# 创建引擎时添加编码参数
engine = create_engine(
    PG_URL, 
    echo=False, 
    pool_pre_ping=True,
    connect_args={
        "client_encoding": "utf8",
        "options": "-c client_encoding=utf8"
    }
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """初始化数据库，创建表和索引"""
    try:
        # 创建pgvector扩展
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
        
        # 创建表
        Base.metadata.create_all(bind=engine)
        
        # 创建向量索引
        with engine.connect() as conn:
            # 检查索引是否存在
            result = conn.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE tablename = 'documents_chunk' 
                AND indexname = 'idx_embedding_cosine'
            """))
            
            if not result.fetchone():
                conn.execute(text("""
                    CREATE INDEX idx_embedding_cosine 
                    ON documents_chunk 
                    USING hnsw (embedding vector_cosine_ops)
                """))
                logger.info("创建向量索引成功")
            conn.commit()
            
    except Exception as e:
        logger.error(f"初始化数据库失败: {e}")
        raise 