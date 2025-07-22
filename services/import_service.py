from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from db import SessionLocal
from models import DocumentChunk
from document_loader import parse_directory, parse_document, generate_document_id
from embedding import get_embedding
from config import MAX_FILE_SIZE_MB
import os
import logging

logger = logging.getLogger(__name__)

class ImportService:
    """文档导入服务"""
    
    async def import_directory(self, directory: str, background_tasks: BackgroundTasks):
        """导入目录"""
        if not os.path.exists(directory):
            raise HTTPException(status_code=400, detail=f"目录不存在: {directory}")
        
        if not os.path.isdir(directory):
            raise HTTPException(status_code=400, detail=f"路径不是目录: {directory}")
        
        # 异步处理导入任务
        background_tasks.add_task(self._process_import, directory)
        
        return {
            "success": True,
            "message": f"开始导入目录: {directory}，处理将在后台进行",
            "total_chunks": 0,
            "processed_files": 0,
            "failed_files": 0
        }
    
    async def sync_directory(self, directory: str, background_tasks: BackgroundTasks):
        """增量同步目录"""
        if not os.path.exists(directory):
            raise HTTPException(status_code=400, detail=f"目录不存在: {directory}")
        
        background_tasks.add_task(self._process_sync, directory)
        
        return {
            "success": True,
            "message": f"开始增量同步目录: {directory}，处理将在后台进行"
        }
    
    def _process_import(self, directory: str):
        """后台处理导入任务"""
        session = None
        try:
            session = SessionLocal()
            logger.info(f"开始处理目录: {directory}")
            chunks = parse_directory(directory)
            
            # 应用批量大小限制
            from config import MAX_BATCH_SIZE
            from config import CHUNKS_PER_FILE_ESTIMATE
            if len(chunks) > MAX_BATCH_SIZE * CHUNKS_PER_FILE_ESTIMATE:
                logger.warning(f"分块数量过多 ({len(chunks)})，建议分批处理")
            
            processed_files = 0
            failed_files = 0
            
            for chunk in chunks:
                try:
                    # 检查是否已存在相同的文档块
                    existing = session.query(DocumentChunk).filter(
                        DocumentChunk.document_id == chunk['meta']['document_id'],
                        DocumentChunk.chunk_index == chunk['chunk_index']
                    ).first()
                    
                    if existing:
                        logger.info(f"跳过已存在的文档块: {chunk['meta']['document_name']} - {chunk['chunk_index']}")
                        continue
                    
                    embedding = get_embedding(chunk['content'])
                    doc = DocumentChunk(
                        document_id=chunk['meta']['document_id'],
                        version=1,
                        document_name=chunk['meta']['document_name'],
                        document_path=chunk['meta']['document_path'],
                        page_num=chunk['meta'].get('page_num'),
                        paragraph_num=chunk['meta'].get('paragraph_num'),
                        chunk_index=chunk['chunk_index'],
                        content=chunk['content'],
                        embedding=embedding,
                        extra_metadata=chunk['meta']
                    )
                    session.add(doc)
                    processed_files += 1
                    
                    # 批量提交，提高性能
                    from config import BATCH_COMMIT_SIZE
                    if processed_files % BATCH_COMMIT_SIZE == 0:
                        session.commit()
                        logger.info(f"已处理 {processed_files} 个文档块")
                        
                except Exception as e:
                    logger.error(f"处理文档块失败: {e}")
                    failed_files += 1
                    try:
                        session.rollback()
                    except Exception as rollback_error:
                        logger.error(f"回滚失败: {rollback_error}")
            
            # 最终提交
            try:
                session.commit()
                logger.info(f"导入完成: 成功 {processed_files} 个，失败 {failed_files} 个")
            except Exception as commit_error:
                logger.error(f"最终提交失败: {commit_error}")
                session.rollback()
            
        except Exception as e:
            logger.error(f"导入过程出错: {e}")
            if session:
                try:
                    session.rollback()
                except Exception as rollback_error:
                    logger.error(f"回滚失败: {rollback_error}")
        finally:
            if session:
                try:
                    session.close()
                except Exception as close_error:
                    logger.error(f"关闭数据库连接失败: {close_error}")
    
    def _process_sync(self, directory: str):
        """后台处理增量同步"""
        session = None
        try:
            session = SessionLocal()
            logger.info(f"开始增量同步目录: {directory}")
            
            # 获取现有文档的信息
            existing_docs = {}
            docs_in_db = session.query(DocumentChunk.document_path, DocumentChunk.document_id).distinct().all()
            for doc in docs_in_db:
                existing_docs[doc.document_path] = doc.document_id
            
            # 扫描目录中的文件
            new_files = []
            updated_files = []
            
            for root, _, files in os.walk(directory):
                for file in files:
                    ext = os.path.splitext(file)[-1].lower()
                    if ext in ['.txt', '.pdf', '.docx', '.xlsx', '.md', '.png', '.jpg', '.jpeg']:
                        file_path = os.path.join(root, file)
                        
                        # 检查文件大小
                        try:
                            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
                            if file_size_mb > MAX_FILE_SIZE_MB:
                                logger.warning(f"跳过过大文件: {file} ({file_size_mb:.1f}MB > {MAX_FILE_SIZE_MB}MB)")
                                continue
                        except OSError as e:
                            logger.error(f"无法获取文件大小: {file} - {e}")
                            continue
                        
                        if file_path in existing_docs:
                            # 检查文件是否被修改
                            current_id = generate_document_id(file_path)
                            if current_id != existing_docs[file_path]:
                                updated_files.append(file_path)
                        else:
                            new_files.append(file_path)
            
            logger.info(f"发现 {len(new_files)} 个新文件，{len(updated_files)} 个更新文件")
            
            # 处理更新的文件（先删除旧版本）
            for file_path in updated_files:
                old_doc_id = existing_docs[file_path]
                session.query(DocumentChunk).filter(
                    DocumentChunk.document_id == old_doc_id
                ).delete()
                logger.info(f"删除旧版本文档: {file_path}")
            
            # 处理新文件和更新文件
            all_files_to_process = new_files + updated_files
            
            # 应用批量大小限制
            from config import MAX_BATCH_SIZE
            if len(all_files_to_process) > MAX_BATCH_SIZE:
                logger.warning(f"文件数量 ({len(all_files_to_process)}) 超过批量限制 ({MAX_BATCH_SIZE})，将只处理前 {MAX_BATCH_SIZE} 个文件")
                all_files_to_process = all_files_to_process[:MAX_BATCH_SIZE]
            
            processed = 0
            
            for file_path in all_files_to_process:
                try:
                    chunks = parse_document(file_path)
                    
                    for chunk in chunks:
                        embedding = get_embedding(chunk['content'])
                        doc = DocumentChunk(
                            document_id=chunk['meta']['document_id'],
                            version=1,
                            document_name=chunk['meta']['document_name'],
                            document_path=chunk['meta']['document_path'],
                            page_num=chunk['meta'].get('page_num'),
                            paragraph_num=chunk['meta'].get('paragraph_num'),
                            chunk_index=chunk['chunk_index'],
                            content=chunk['content'],
                            embedding=embedding,
                            extra_metadata=chunk['meta']
                        )
                        session.add(doc)
                    
                    processed += 1
                    from config import BATCH_COMMIT_SIZE
                    if processed % BATCH_COMMIT_SIZE == 0:
                        session.commit()
                        logger.info(f"已同步 {processed}/{len(all_files_to_process)} 个文件")
                        
                except Exception as e:
                    logger.error(f"同步文件失败 {file_path}: {e}")
            
            session.commit()
            logger.info(f"增量同步完成: 处理了 {processed} 个文件")
            
        except Exception as e:
            logger.error(f"增量同步出错: {e}")
            if session:
                try:
                    session.rollback()
                except Exception as rollback_error:
                    logger.error(f"回滚失败: {rollback_error}")
        finally:
            if session:
                try:
                    session.close()
                except Exception as close_error:
                    logger.error(f"关闭数据库连接失败: {close_error}")