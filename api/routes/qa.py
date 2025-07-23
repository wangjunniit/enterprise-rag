import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from config import QUESTION_MAX_LENGTH, SEARCH_DEFAULT_LIMIT
from services.qa_service import QAService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/qa", tags=["智能问答"])

class QARequest(BaseModel):
    question: str = Field(..., description="用户问题", min_length=1, max_length=QUESTION_MAX_LENGTH)
    history: Optional[List[List[str]]] = Field(None, description="对话历史 [[user, assistant], ...]")

class QAResponse(BaseModel):
    answer: str
    sources: Optional[List[dict]] = None

@router.post('', response_model=QAResponse)
async def qa(request: QARequest):
    """问答接口：向量召回+重排序+LLM生成"""
    qa_service = QAService()
    return await qa_service.answer_question(request)

@router.post('/batch')
async def batch_qa(questions: List[str]):
    """批量问答接口"""
    if len(questions) > 10:
        raise HTTPException(status_code=400, detail="批量问答最多支持10个问题")
    
    qa_service = QAService()
    return await qa_service.batch_answer(questions)

@router.get('/search')
async def search_content(query: str, limit: int = SEARCH_DEFAULT_LIMIT):
    """基于内容的文本搜索（非向量搜索）"""
    qa_service = QAService()
    return await qa_service.search_content(query, limit)