import logging

from fastapi import HTTPException

from db import SessionLocal
from models import DocumentChunk

logger = logging.getLogger(__name__)

class DocumentService:
    """文档管理服务"""
    
    async def list_documents(self, skip: int = 0, limit: int = 100, search: str = None):
        """获取文档列表，支持搜索"""
        session = SessionLocal()
        try:
            # 构建查询
            query = session.query(
                DocumentChunk.document_id,
                DocumentChunk.document_name,
                DocumentChunk.document_path,
                DocumentChunk.created_at
            ).distinct(DocumentChunk.document_id)
            
            # 添加搜索条件
            if search:
                query = query.filter(
                    DocumentChunk.document_name.ilike(f'%{search}%')
                )
            
            docs = query.offset(skip).limit(limit).all()
            
            # 获取每个文档的分块数量
            result_docs = []
            for doc in docs:
                chunk_count = session.query(DocumentChunk).filter(
                    DocumentChunk.document_id == doc.document_id
                ).count()
                
                result_docs.append({
                    "document_id": doc.document_id,
                    "document_name": doc.document_name,
                    "document_path": doc.document_path,
                    "created_at": doc.created_at.isoformat(),
                    "chunk_count": chunk_count
                })
            
            return {"documents": result_docs}
        except Exception as e:
            logger.error(f"获取文档列表失败: {e}")
            raise HTTPException(status_code=500, detail="获取文档列表失败")
        finally:
            session.close()
    
    async def delete_document(self, document_id: str):
        """删除指定文档的所有分块"""
        session = SessionLocal()
        try:
            deleted_count = session.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).delete()
            session.commit()
            
            if deleted_count == 0:
                raise HTTPException(status_code=404, detail="文档不存在")
            
            return {"message": f"成功删除文档，共删除 {deleted_count} 个分块"}
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            session.rollback()
            raise HTTPException(status_code=500, detail="删除文档失败")
        finally:
            session.close()
    
    async def get_document_chunks(self, document_id: str, skip: int = 0, limit: int = 50):
        """获取指定文档的所有分块"""
        session = SessionLocal()
        try:
            chunks = session.query(DocumentChunk).filter(
                DocumentChunk.document_id == document_id
            ).order_by(DocumentChunk.chunk_index).offset(skip).limit(limit).all()
            
            if not chunks:
                raise HTTPException(status_code=404, detail="文档不存在")
            
            return {
                "document_id": document_id,
                "chunks": [
                    {
                        "id": chunk.id,
                        "chunk_index": chunk.chunk_index,
                        "content": chunk.content,
                        "page_num": chunk.page_num,
                        "paragraph_num": chunk.paragraph_num,
                        "created_at": chunk.created_at.isoformat()
                    } for chunk in chunks
                ]
            }
        except Exception as e:
            logger.error(f"获取文档分块失败: {e}")
            raise HTTPException(status_code=500, detail="获取文档分块失败")
        finally:
            session.close()
    
    async def clear_all_documents(self):
        """清空所有文档（危险操作）"""
        session = SessionLocal()
        try:
            deleted_count = session.query(DocumentChunk).delete()
            session.commit()
            
            return {"message": f"成功清空所有文档，共删除 {deleted_count} 个分块"}
        except Exception as e:
            logger.error(f"清空文档失败: {e}")
            session.rollback()
            raise HTTPException(status_code=500, detail="清空文档失败")
        finally:
            session.close()