from fastapi import APIRouter, HTTPException
import logging
from services.system_service import SystemService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/system", tags=["系统监控"])

@router.get('/health')
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "timestamp": "2025-01-22"}

@router.get('/stats')
async def get_stats():
    """获取系统统计信息"""
    system_service = SystemService()
    return await system_service.get_stats()

@router.get('/info')
async def get_system_info():
    """获取系统信息"""
    system_service = SystemService()
    return await system_service.get_system_info()

@router.get('/model_status')
async def get_model_status():
    """获取模型加载状态"""
    system_service = SystemService()
    return await system_service.get_model_status()