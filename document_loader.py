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

# 导入额外的解析库
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from docx import Document
except ImportError:
    Document = None

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

def create_chunks_with_metadata(text: str, file_path: str, page_paragraphs: List[Dict] = None) -> List[Dict[str, Any]]:
    """创建带有页码和段落号的分块"""
    if not text.strip():
        return []
    
    # 分块
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, 
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", "。", "！", "？", ".", "!", "?", " ", ""]
    )
    chunks = splitter.split_text(text)
    
    # 生成文档ID和基础元数据
    document_id = generate_document_id(file_path)
    ext = os.path.splitext(file_path)[-1].lower()
    base_meta = {
        'document_id': document_id,
        'document_name': os.path.basename(file_path),
        'document_path': file_path,
        'file_size': os.path.getsize(file_path),
        'file_ext': ext
    }
    
    result = []
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
            
        # 查找该分块对应的页码和段落号
        page_num = None
        paragraph_num = None
        
        if page_paragraphs:
            # 在原文中查找分块的位置
            chunk_start = text.find(chunk.strip()[:50])  # 使用前50个字符定位
            if chunk_start >= 0:
                # 找到最接近的页码和段落号
                for pp in page_paragraphs:
                    if pp['start_pos'] <= chunk_start <= pp['end_pos']:
                        page_num = pp['page_num']
                        paragraph_num = pp['paragraph_num']
                        break
                    elif chunk_start >= pp['start_pos']:
                        # 如果没有完全匹配，使用最近的
                        page_num = pp['page_num']
                        paragraph_num = pp['paragraph_num']
        
        chunk_meta = base_meta.copy()
        chunk_meta['page_num'] = page_num
        chunk_meta['paragraph_num'] = paragraph_num
        
        result.append({
            'content': chunk.strip(),
            'chunk_index': i,
            'meta': chunk_meta
        })
    
    return result

def parse_pdf_with_structure(file_path: str) -> List[Dict[str, Any]]:
    """解析PDF文件并提取页码信息"""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        
        full_text = ""
        page_paragraphs = []
        current_pos = 0
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            
            if page_text.strip():
                # 按段落分割
                paragraphs = [p.strip() for p in page_text.split('\n\n') if p.strip()]
                
                for para_num, paragraph in enumerate(paragraphs, 1):
                    start_pos = current_pos
                    end_pos = current_pos + len(paragraph)
                    
                    page_paragraphs.append({
                        'page_num': page_num + 1,
                        'paragraph_num': para_num,
                        'start_pos': start_pos,
                        'end_pos': end_pos,
                        'content': paragraph
                    })
                    
                    full_text += paragraph + "\n\n"
                    current_pos = len(full_text)
        
        doc.close()
        
        if not full_text.strip():
            logger.warning(f"PDF文档内容为空: {file_path}")
            return []
        
        return create_chunks_with_metadata(full_text, file_path, page_paragraphs)
        
    except Exception as e:
        logger.error(f"PDF解析失败 {file_path}: {e}")
        # 降级到简单解析
        return parse_text_with_structure(file_path)

def parse_docx_with_structure(file_path: str) -> List[Dict[str, Any]]:
    """解析Word文档并提取段落信息"""
    try:
        from docx import Document
        doc = Document(file_path)
        
        full_text = ""
        page_paragraphs = []
        current_pos = 0
        
        for para_num, paragraph in enumerate(doc.paragraphs, 1):
            para_text = paragraph.text.strip()
            if para_text:
                start_pos = current_pos
                end_pos = current_pos + len(para_text)
                
                page_paragraphs.append({
                    'page_num': 1,  # Word文档没有明确的页码概念，统一设为1
                    'paragraph_num': para_num,
                    'start_pos': start_pos,
                    'end_pos': end_pos,
                    'content': para_text
                })
                
                full_text += para_text + "\n\n"
                current_pos = len(full_text)
        
        if not full_text.strip():
            logger.warning(f"Word文档内容为空: {file_path}")
            return []
        
        return create_chunks_with_metadata(full_text, file_path, page_paragraphs)
        
    except Exception as e:
        logger.error(f"Word文档解析失败 {file_path}: {e}")
        # 降级到简单解析
        return parse_text_with_structure(file_path)

def parse_excel_with_structure(file_path: str) -> List[Dict[str, Any]]:
    """解析Excel文件并提取工作表信息"""
    try:
        excel_file = pd.ExcelFile(file_path)
        full_text = ""
        page_paragraphs = []
        current_pos = 0
        
        for sheet_num, sheet_name in enumerate(excel_file.sheet_names, 1):
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            sheet_text = f"工作表: {sheet_name}\n"
            sheet_text += df.to_string(index=False, na_rep='')
            
            if sheet_text.strip():
                start_pos = current_pos
                end_pos = current_pos + len(sheet_text)
                
                page_paragraphs.append({
                    'page_num': sheet_num,  # 将工作表编号作为页码
                    'paragraph_num': 1,
                    'start_pos': start_pos,
                    'end_pos': end_pos,
                    'content': sheet_text
                })
                
                full_text += sheet_text + "\n\n"
                current_pos = len(full_text)
        
        if not full_text.strip():
            logger.warning(f"Excel文档内容为空: {file_path}")
            return []
        
        return create_chunks_with_metadata(full_text, file_path, page_paragraphs)
        
    except Exception as e:
        logger.error(f"Excel解析失败 {file_path}: {e}")
        return []

def parse_markdown_with_structure(file_path: str) -> List[Dict[str, Any]]:
    """解析Markdown文件并提取标题层级信息"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            logger.warning(f"Markdown文档内容为空: {file_path}")
            return []
        
        # 按标题分段
        lines = content.split('\n')
        full_text = ""
        page_paragraphs = []
        current_pos = 0
        para_num = 0
        current_section = ""
        
        for line in lines:
            if line.strip().startswith('#'):
                # 新的标题段落
                if current_section.strip():
                    para_num += 1
                    start_pos = current_pos
                    end_pos = current_pos + len(current_section)
                    
                    page_paragraphs.append({
                        'page_num': 1,
                        'paragraph_num': para_num,
                        'start_pos': start_pos,
                        'end_pos': end_pos,
                        'content': current_section.strip()
                    })
                    
                    full_text += current_section + "\n"
                    current_pos = len(full_text)
                
                current_section = line + "\n"
            else:
                current_section += line + "\n"
        
        # 处理最后一段
        if current_section.strip():
            para_num += 1
            start_pos = current_pos
            end_pos = current_pos + len(current_section)
            
            page_paragraphs.append({
                'page_num': 1,
                'paragraph_num': para_num,
                'start_pos': start_pos,
                'end_pos': end_pos,
                'content': current_section.strip()
            })
            
            full_text += current_section
        
        return create_chunks_with_metadata(full_text, file_path, page_paragraphs)
        
    except Exception as e:
        logger.error(f"Markdown解析失败 {file_path}: {e}")
        return []

def parse_text_with_structure(file_path: str) -> List[Dict[str, Any]]:
    """解析文本文件并按段落分割"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content.strip():
            logger.warning(f"文本文档内容为空: {file_path}")
            return []
        
        # 按段落分割
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        full_text = ""
        page_paragraphs = []
        current_pos = 0
        
        for para_num, paragraph in enumerate(paragraphs, 1):
            start_pos = current_pos
            end_pos = current_pos + len(paragraph)
            
            page_paragraphs.append({
                'page_num': 1,
                'paragraph_num': para_num,
                'start_pos': start_pos,
                'end_pos': end_pos,
                'content': paragraph
            })
            
            full_text += paragraph + "\n\n"
            current_pos = len(full_text)
        
        return create_chunks_with_metadata(full_text, file_path, page_paragraphs)
        
    except Exception as e:
        logger.error(f"文本解析失败 {file_path}: {e}")
        return []

def parse_image_with_structure(file_path: str) -> List[Dict[str, Any]]:
    """解析图片文件并OCR提取文本"""
    try:
        text = ocr_image(file_path)
        
        if not text.strip():
            logger.warning(f"图片OCR内容为空: {file_path}")
            return []
        
        # 图片只有一个段落
        page_paragraphs = [{
            'page_num': 1,
            'paragraph_num': 1,
            'start_pos': 0,
            'end_pos': len(text),
            'content': text
        }]
        
        return create_chunks_with_metadata(text, file_path, page_paragraphs)
        
    except Exception as e:
        logger.error(f"图片解析失败 {file_path}: {e}")
        return []

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
    
    try:
        # 根据文件类型解析并获取结构化信息
        if ext == '.pdf':
            return parse_pdf_with_structure(file_path)
        elif ext == '.docx':
            return parse_docx_with_structure(file_path)
        elif ext == '.xlsx':
            return parse_excel_with_structure(file_path)
        elif ext == '.md':
            return parse_markdown_with_structure(file_path)
        elif ext == '.txt':
            return parse_text_with_structure(file_path)
        elif ext in ['.png', '.jpg', '.jpeg']:
            return parse_image_with_structure(file_path)
        else:
            # 默认按文本处理
            return parse_text_with_structure(file_path)
        
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