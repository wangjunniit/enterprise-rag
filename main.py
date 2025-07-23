import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# 导入路由
from api.routes.documents import router as documents_router
from api.routes.qa import router as qa_router
from api.routes.system import router as system_router
from config import DEBUG
from db import init_db
from utils import setup_logging

# 修复Windows上的asyncio连接重置错误

# 设置日志
setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="企业RAG知识库",
    description="基于Qwen系列模型的企业内部RAG应用",
    version="1.0.0",
    debug=DEBUG
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 注册路由
app.include_router(documents_router)
app.include_router(qa_router)
app.include_router(system_router)

# 初始化数据库和模型
@app.on_event("startup")
async def startup_event():
    logger.info("正在初始化数据库...")
    init_db()
    logger.info("数据库初始化完成")
    
    # 预加载模型
    logger.info("正在预加载模型...")
    try:
        from embedding import get_embedding_model
        from llm import get_llm_model  
        from rerank import get_rerank_model
        
        logger.info("正在加载向量化模型...")
        get_embedding_model()
        logger.info("向量化模型加载完成")
        
        logger.info("正在加载LLM模型...")
        get_llm_model()
        logger.info("LLM模型加载完成")
        
        logger.info("正在加载重排序模型...")
        get_rerank_model()
        logger.info("重排序模型加载完成")
        
        logger.info("所有模型预加载完成")
    except Exception as e:
        logger.error(f"模型预加载失败: {e}")
        # 不抛出异常，允许程序继续运行

@app.get("/")
async def root():
    """返回Web界面"""
    return FileResponse('static/index.html')

@app.get("/api")
async def api_info():
    """API信息"""
    return {"message": "企业RAG知识库API", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    from config import APP_HOST, APP_PORT
    uvicorn.run(app, host=APP_HOST, port=APP_PORT)