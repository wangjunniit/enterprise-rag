from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

Base = declarative_base()

class DocumentChunk(Base):
    __tablename__ = 'documents_chunk'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String, nullable=False, index=True)  # 文档唯一标识
    version = Column(Integer, default=1, nullable=False)
    document_name = Column(String, nullable=False)
    document_path = Column(String, nullable=False)
    page_num = Column(Integer)
    paragraph_num = Column(Integer)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1024), nullable=False)  # Qwen3-Embedding-0.6B实际输出1024维向量
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    extra_metadata = Column(JSON)
    
    # 添加复合索引优化查询
    __table_args__ = (
        Index('idx_document_version', 'document_id', 'version'),
        Index('idx_created_at', 'created_at'),
        # 向量索引需要在数据库中手动创建
    ) 