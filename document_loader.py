import hashlib
import logging
import os
from typing import List, Dict, Any

import pandas as pd
import pytesseract
from PIL import Image
# 分块工具
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader,
    PyMuPDFLoader,
    Docx2txtLoader,
    UnstructuredMarkdownLoader
)

from config import CHUNK_SIZE, CHUNK_OVERLAP, SUPPORTED_EXTS, MAX_FILE_SIZE_MB

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_loader(file_path: str):
    """根据文件扩展名选择合适的加载器"""
    ext = os.path.splitext(file_path)[-1].lower()
    try:
        if ext == '.txt':
            return TextLoader(file_path, encoding='utf-8')
        elif ext == '.pdf':
            return PyMuPDFLoader(file_path)  # 修复：使用PyMuPDFLoader
        elif ext == '.docx':
            return Docx2txtLoader(file_path)
        elif ext == '.xlsx':
            return None  # Excel单独处理
        elif ext == '.md':
            return UnstructuredMarkdownLoader(file_path)
        elif ext in ['.png', '.jpg', '.jpeg']:
            return None  # 图片单独处理
        else:
            return TextLoader(file_path, encoding='utf-8')  # 默认按文本处理
    except Exception as e:
        logger.error(f"创建加载器失败 {file_path}: {e}")
        return None

def ocr_image(file_path: str) -> str:
    """OCR图片提取文本"""
    try:
        image = Image.open(file_path)
        text = pytesseract.image_to_string(image, lang='chi_sim+eng')
        return text.strip()
    except Exception as e:
        logger.error(f"OCR处理失败 {file_path}: {e}")
        return ""

def parse_excel(file_path: str) -> str:
    """解析Excel文件"""
    try:
        # 读取所有sheet
        excel_file = pd.ExcelFile(file_path)
        all_text = []
        for sheet_name in excel_file.sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            # 将DataFrame转换为文本
            sheet_text = f"工作表: {sheet_name}\n"
            sheet_text += df.to_string(index=False, na_rep='')
            all_text.append(sheet_text)
        return '\n\n'.join(all_text)
    except Exception as e:
        logger.error(f"Excel解析失败 {file_path}: {e}")
        return ""

def generate_document_id(file_path: str) -> str:
    """生成文档唯一ID"""
    # 使用文件路径和修改时间生成唯一ID
    stat = os.stat(file_path)
    content = f"{file_path}_{stat.st_mtime}_{stat.st_size}"
    return hashlib.md5(content.encode()).hexdigest()

def parse_document(file_path: str) -> List[Dict[str, Any]]:
    """解析单个文档"""
    if not os.path.exists(file_path):
        logger.error(f"文件不存在: {file_path}")
        return []
    
    # 检查文件大小
    try:
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            logger.warning(f"跳过过大文件: {os.path.basename(file_path)} ({file_size_mb:.1f}MB > {MAX_FILE_SIZE_MB}MB)")
            return []
    except OSError as e:
        logger.error(f"无法获取文件大小: {file_path} - {e}")
        return []
    
    ext = os.path.splitext(file_path)[-1].lower()
    text = ""
    
    try:
        loader = get_loader(file_path)
        if loader:
            docs = loader.load()
            text = '\n'.join([doc.page_content for doc in docs])
        elif ext == '.xlsx':
            text = parse_excel(file_path)
        elif ext in ['.png', '.jpg', '.jpeg']:
            text = ocr_image(file_path)
        else:
            logger.warning(f"不支持的文件格式: {file_path}")
            return []
            
        if not text.strip():
            logger.warning(f"文档内容为空: {file_path}")
            return []
            
        # 分块
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE, 
            chunk_overlap=CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
        )
        chunks = splitter.split_text(text)
        
        # 生成文档ID和元数据
        document_id = generate_document_id(file_path)
        meta = {
            'document_id': document_id,
            'document_name': os.path.basename(file_path),
            'document_path': file_path,
            'file_size': os.path.getsize(file_path),
            'file_ext': ext
        }
        
        result = []
        for i, chunk in enumerate(chunks):
            if chunk.strip():  # 只保留非空分块
                result.append({
                    'content': chunk.strip(),
                    'chunk_index': i,
                    'meta': meta.copy()
                })
        
        logger.info(f"成功解析文档 {file_path}, 生成 {len(result)} 个分块")
        return result
        
    except Exception as e:
        logger.error(f"解析文档失败 {file_path}: {e}")
        return []

def parse_directory(directory: str) -> List[Dict[str, Any]]:
    """递归解析目录下的所有支持文档"""
    if not os.path.exists(directory):
        logger.error(f"目录不存在: {directory}")
        return []
    
    if not os.path.isdir(directory):
        logger.error(f"路径不是目录: {directory}")
        return []
    
    all_chunks = []
    processed_files = 0
    failed_files = 0
    
    logger.info(f"开始解析目录: {directory}")
    
    for root, _, files in os.walk(directory):
        for file in files:
            ext = os.path.splitext(file)[-1].lower()
            if ext in SUPPORTED_EXTS:
                file_path = os.path.join(root, file)
                try:
                    chunks = parse_document(file_path)
                    all_chunks.extend(chunks)
                    processed_files += 1
                    if chunks:
                        logger.info(f"处理文件 {file}: {len(chunks)} 个分块")
                    else:
                        logger.warning(f"文件无内容或处理失败: {file}")
                        failed_files += 1
                except Exception as e:
                    logger.error(f"处理文件失败 {file}: {e}")
                    failed_files += 1
    
    logger.info(f"目录解析完成: 处理 {processed_files} 个文件, 失败 {failed_files} 个, 总共 {len(all_chunks)} 个分块")
    return all_chunks 