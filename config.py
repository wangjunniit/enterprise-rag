import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ===================== Hugging Face 镜像配置 =====================
HF_ENDPOINT = os.getenv('HF_ENDPOINT', 'https://huggingface.co')  # Hugging Face 镜像站地址
# 设置环境变量，让transformers库使用镜像
if HF_ENDPOINT != 'https://huggingface.co':
    os.environ['HF_ENDPOINT'] = HF_ENDPOINT

# ===================== 数据库配置 =====================
PG_HOST = os.getenv('PG_HOST', 'localhost')         # PostgreSQL主机地址
PG_PORT = int(os.getenv('PG_PORT', 5432))           # PostgreSQL端口
PG_USER = os.getenv('PG_USER', 'postgres')          # 数据库用户名
PG_PASSWORD = os.getenv('PG_PASSWORD', 'postgres')  # 数据库密码
PG_DB = os.getenv('PG_DB', 'rag')                   # 数据库名
PG_URL = f'postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DB}?client_encoding=utf8'  # SQLAlchemy连接URL

# ===================== 模型配置 =====================
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'Qwen/Qwen3-Embedding-0.6B')  # 向量化模型名称
RERANK_MODEL = os.getenv('RERANK_MODEL', 'Qwen/Qwen3-Reranker-0.6B')         # 重排序模型名称
LLM_MODEL = os.getenv('LLM_MODEL', 'Qwen/Qwen3-0.6B')                        # LLM生成模型名称

# ===================== 模型运行配置 =====================
DEVICE = os.getenv('DEVICE', 'auto')                    # 设备选择：auto, cpu, cuda
MODEL_CACHE_DIR = os.getenv('MODEL_CACHE_DIR', './models')  # 模型缓存目录
MAX_MEMORY_GB = int(os.getenv('MAX_MEMORY_GB', 8))       # 最大内存使用量(GB)

# ===================== 文档分块与检索参数 =====================
CHUNK_SIZE = int(os.getenv('CHUNK_SIZE', 400))           # 文档分块大小（token数）
CHUNK_OVERLAP = int(os.getenv('CHUNK_OVERLAP', 100))     # 分块重叠部分（token数）
TOP_K = int(os.getenv('TOP_K', 10))                      # 检索时召回Top-K文档块
TOP_N = int(os.getenv('TOP_N', 5))                       # 重排序后选取Top-N文档块注入Prompt
HISTORY_ROUNDS = int(os.getenv('HISTORY_ROUNDS', 5))     # 多轮对话拼接的最大轮数
MAX_HISTORY_TOKENS = int(os.getenv('MAX_HISTORY_TOKENS', 800))  # 多轮对话拼接的最大token数
SUPPORTED_EXTS = [         # 支持的文档扩展名
    '.txt', '.pdf', '.docx', '.xlsx', '.md', '.png', '.jpg', '.jpeg'
]

# ===================== 应用配置 =====================
APP_HOST = os.getenv('APP_HOST', '0.0.0.0')
APP_PORT = int(os.getenv('APP_PORT', 8000))
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# ===================== 模型推理配置 =====================
EMBEDDING_MAX_LENGTH = int(os.getenv('EMBEDDING_MAX_LENGTH', 512))    # 向量化模型最大输入长度
RERANK_MAX_LENGTH = int(os.getenv('RERANK_MAX_LENGTH', 512))          # 重排序模型最大输入长度
LLM_INPUT_MAX_LENGTH = int(os.getenv('LLM_INPUT_MAX_LENGTH', 1024))   # LLM输入最大长度
LLM_OUTPUT_MAX_LENGTH = int(os.getenv('LLM_OUTPUT_MAX_LENGTH', 2048)) # LLM输出最大长度
LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', 0.7))            # LLM生成温度

# ===================== API配置 =====================
QUESTION_MAX_LENGTH = int(os.getenv('QUESTION_MAX_LENGTH', 1000))     # 用户问题最大长度
DEFAULT_PAGE_SIZE = int(os.getenv('DEFAULT_PAGE_SIZE', 100))          # 默认分页大小
SEARCH_DEFAULT_LIMIT = int(os.getenv('SEARCH_DEFAULT_LIMIT', 20))     # 搜索默认限制
CHUNKS_PAGE_SIZE = int(os.getenv('CHUNKS_PAGE_SIZE', 50))             # 文档分块分页大小
BATCH_COMMIT_SIZE = int(os.getenv('BATCH_COMMIT_SIZE', 10))           # 批量提交大小

# ===================== 系统配置 =====================
LOG_FILE_NAME = os.getenv('LOG_FILE_NAME', 'rag_app.log')            # 日志文件名
TOKEN_ESTIMATE_RATIO = float(os.getenv('TOKEN_ESTIMATE_RATIO', 2.0))  # Token估算比例(字符/token)
CHUNKS_PER_FILE_ESTIMATE = int(os.getenv('CHUNKS_PER_FILE_ESTIMATE', 10))  # 每个文件预估分块数
CONTENT_PREVIEW_LENGTH = int(os.getenv('CONTENT_PREVIEW_LENGTH', 200))  # 内容预览长度
SEARCH_CONTENT_PREVIEW_LENGTH = int(os.getenv('SEARCH_CONTENT_PREVIEW_LENGTH', 300))  # 搜索结果内容预览长度

# ===================== 安全配置 =====================
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 100))  # 最大文件大小限制
MAX_BATCH_SIZE = int(os.getenv('MAX_BATCH_SIZE', 50))       # 批量处理最大文件数 