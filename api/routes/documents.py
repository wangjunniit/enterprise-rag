from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
import logging
from services.document_service import DocumentService
from services.import_service import ImportService
from config import DEFAULT_PAGE_SIZE, CHUNKS_PAGE_SIZE

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["文档管理"])

class ImportRequest(BaseModel):
    directory: str = Field(..., description="要导入的目录路径")

class ImportResponse(BaseModel):
    success: bool
    message: str
    total_chunks: int = 0
    processed_files: int = 0
    failed_files: int = 0

@router.post('/import', response_model=ImportResponse)
async def import_directory(request: ImportRequest, background_tasks: BackgroundTasks):
    """递归导入目录下所有文档，分块、向量化并入库"""
    import_service = ImportService()
    return await import_service.import_directory(request.directory, background_tasks)

@router.post('/sync')
async def sync_directory(request: ImportRequest, background_tasks: BackgroundTasks):
    """增量同步目录 - 只处理新增或修改的文件"""
    import_service = ImportService()
    return await import_service.sync_directory(request.directory, background_tasks)

@router.get('')
async def list_documents(skip: int = 0, limit: int = 100, search: str = None):
    """获取文档列表，支持搜索"""
    document_service = DocumentService()
    return await document_service.list_documents(skip, limit, search)

@router.delete('/{document_id}')
async def delete_document(document_id: str):
    """删除指定文档的所有分块"""
    document_service = DocumentService()
    return await document_service.delete_document(document_id)

@router.get('/{document_id}/chunks')
async def get_document_chunks(document_id: str, skip: int = 0, limit: int = 50):
    """获取指定文档的所有分块"""
    document_service = DocumentService()
    return await document_service.get_document_chunks(document_id, skip, limit)

@router.post('/clear_all')
async def clear_all_documents():
    """清空所有文档（危险操作）"""
    document_service = DocumentService()
    return await document_service.clear_all_documents()