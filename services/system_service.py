from fastapi import HTTPException
from sqlalchemy.orm import Session
from db import SessionLocal
from models import DocumentChunk
from config import EMBEDDING_MODEL, RERANK_MODEL, LLM_MODEL
import logging

logger = logging.getLogger(__name__)

class SystemService:
    """系统服务"""
    
    async def get_stats(self):
        """获取系统统计信息"""
        session = SessionLocal()
        try:
            total_chunks = session.query(DocumentChunk).count()
            total_docs = session.query(DocumentChunk.document_id).distinct().count()
            
            return {
                "total_documents": total_docs,
                "total_chunks": total_chunks,
                "avg_chunks_per_doc": round(total_chunks / total_docs, 2) if total_docs > 0 else 0
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            raise HTTPException(status_code=500, detail="获取统计信息失败")
        finally:
            session.close()
    
    async def get_system_info(self):
        """获取系统信息"""
        try:
            from utils import get_system_info
            return get_system_info()
        except Exception as e:
            logger.error(f"获取系统信息失败: {e}")
            raise HTTPException(status_code=500, detail="获取系统信息失败")
    
    async def get_model_status(self):
        """获取模型加载状态"""
        try:
            from embedding import _embedding_model
            from rerank import _rerank_model
            from llm import _llm_model
            
            return {
                "embedding_model": {
                    "loaded": _embedding_model is not None,
                    "model_name": EMBEDDING_MODEL if _embedding_model else None
                },
                "rerank_model": {
                    "loaded": _rerank_model is not None,
                    "model_name": RERANK_MODEL if _rerank_model else None
                },
                "llm_model": {
                    "loaded": _llm_model is not None,
                    "model_name": LLM_MODEL if _llm_model else None
                }
            }
        except Exception as e:
            logger.error(f"获取模型状态失败: {e}")
            raise HTTPException(status_code=500, detail="获取模型状态失败")