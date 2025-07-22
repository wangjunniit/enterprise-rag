from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from db import SessionLocal
from models import DocumentChunk
from embedding import get_embedding
from rerank import rerank
from llm import generate_answer
from config import TOP_K, TOP_N, HISTORY_ROUNDS, CONTENT_PREVIEW_LENGTH, SEARCH_CONTENT_PREVIEW_LENGTH
from utils import timer
import logging

logger = logging.getLogger(__name__)

class QAService:
    """问答服务"""
    
    @timer
    async def answer_question(self, request):
        """回答单个问题"""
        session = SessionLocal()
        try:
            # 1. 查询向量
            q_emb = get_embedding(request.question)
            
            # 2. 检索Top-K
            docs_with_distance = session.query(
                DocumentChunk,
                DocumentChunk.embedding.l2_distance(q_emb).label('distance')
            ).order_by(
                DocumentChunk.embedding.l2_distance(q_emb)
            ).limit(TOP_K).all()
            
            if not docs_with_distance:
                return {"answer": "未找到相关信息", "sources": []}
            
            # 3. 重排序
            doc_list = [
                {
                    'content': doc.content, 
                    'meta': {
                        'document_name': doc.document_name,
                        'page_num': doc.page_num,
                        'paragraph_num': doc.paragraph_num,
                        'distance': float(distance)
                    }
                } for doc, distance in docs_with_distance
            ]
            reranked = rerank(request.question, doc_list)[:TOP_N]
            
            # 4. 构造Prompt
            history_lines = []
            if request.history:
                from config import MAX_HISTORY_TOKENS
                current_tokens = 0
                
                # 从最新的对话开始，逐步添加历史对话，直到达到token限制
                for turn in reversed(request.history[-HISTORY_ROUNDS:]):
                    if len(turn) >= 2:
                        user, assistant = turn[0], turn[1]
                        turn_text = f"用户：{user}\n助手：{assistant}"
                        
                        # 简单估算token数（中文约1.5字符/token，英文约4字符/token）
                        from config import TOKEN_ESTIMATE_RATIO
                        estimated_tokens = int(len(turn_text) / TOKEN_ESTIMATE_RATIO)
                        
                        if current_tokens + estimated_tokens > MAX_HISTORY_TOKENS:
                            break
                        
                        history_lines.insert(0, f"用户：{user}")
                        history_lines.insert(1, f"助手：{assistant}")
                        current_tokens += estimated_tokens
                        
            history_str = '\n'.join(history_lines)
            
            context_str = ''
            sources = []
            for idx, doc in enumerate(reranked, 1):
                meta = doc['meta']
                context_str += f"{idx}. {doc['content']}\n   出处：{meta.get('document_name','')}，页码：{meta.get('page_num','')}，段落：{meta.get('paragraph_num','')}\n"
                sources.append({
                    'document_name': meta.get('document_name', ''),
                    'page_num': meta.get('page_num'),
                    'paragraph_num': meta.get('paragraph_num'),
                    'content': doc['content'][:CONTENT_PREVIEW_LENGTH] + '...' if len(doc['content']) > CONTENT_PREVIEW_LENGTH else doc['content'],
                    'score': doc.get('score', 0),
                    'distance': meta.get('distance', 0)
                })
            
            prompt = f"""你是企业知识库智能助手，请严格根据下列资料内容回答用户问题。
如资料中未提及，请回复"未找到相关信息"，不要编造答案。
如有多条信息请用分点或表格展示，答案后请注明引用的资料出处（如文档名、页码、段落号）。

【历史对话】
{history_str}

【参考资料】
{context_str}

【用户问题】
{request.question}

【你的回答】"""
            
            # 5. LLM生成
            answer = generate_answer(prompt)
            return {"answer": answer, "sources": sources}
            
        except Exception as e:
            logger.error(f"问答处理失败: {e}")
            raise HTTPException(status_code=500, detail=f"处理问题时出错: {str(e)}")
        finally:
            session.close()
    
    async def batch_answer(self, questions: list):
        """批量问答"""
        results = []
        for question in questions:
            try:
                from api.routes.qa import QARequest
                request = QARequest(question=question, history=[])
                response = await self.answer_question(request)
                results.append({
                    "question": question,
                    "answer": response["answer"],
                    "success": True
                })
            except Exception as e:
                results.append({
                    "question": question,
                    "error": str(e),
                    "success": False
                })
        
        return {"results": results}
    
    async def search_content(self, query: str, limit: int = 20):
        """基于内容的文本搜索"""
        session = SessionLocal()
        try:
            chunks = session.query(DocumentChunk).filter(
                DocumentChunk.content.ilike(f'%{query}%')
            ).limit(limit).all()

            results = []
            for chunk in chunks:
                content = getattr(chunk, 'content', '') or ''
                preview = content[:SEARCH_CONTENT_PREVIEW_LENGTH] + '...' if len(content) > SEARCH_CONTENT_PREVIEW_LENGTH else content
                results.append({
                    "document_id": chunk.document_id,
                    "document_name": chunk.document_name,
                    "chunk_index": chunk.chunk_index,
                    "content": preview,
                    "page_num": chunk.page_num,
                    "paragraph_num": chunk.paragraph_num
                })

            return {
                "query": query,
                "results": results
            }
        except Exception as e:
            logger.error(f"内容搜索失败: {e}")
            raise HTTPException(status_code=500, detail="内容搜索失败")
        finally:
            session.close()