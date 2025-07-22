# 🤖 企业RAG知识库

基于Qwen系列模型的企业内部RAG（检索增强生成）应用，支持多种文档格式的智能问答。

## ✨ 主要功能

- 📁 **多格式文档支持**: 支持txt、pdf、docx、xlsx、markdown、图片等格式
- 🔍 **智能检索**: 基于向量相似度的语义检索
- 🎯 **重排序优化**: 使用Qwen3-Reranker提升检索精度
- 💬 **多轮对话**: 支持上下文感知的多轮问答
- 🔄 **增量同步**: 支持目录的增量更新
- 🌐 **Web界面**: 提供友好的Web管理界面
- 📊 **统计监控**: 实时查看系统状态和文档统计

## 🏗️ 技术架构

### 核心技术栈
- **开发语言**: Python 3.8+
- **Web框架**: FastAPI
- **数据库**: PostgreSQL + pgvector
- **向量化模型**: Qwen/Qwen3-Embedding-0.6B
- **重排序模型**: Qwen/Qwen3-Reranker-0.6B  
- **生成模型**: Qwen/Qwen3-0.6B

### 系统流程
1. **文档预处理**: 解析多种格式文档
2. **向量化**: 使用Qwen3-Embedding将文档分块转换为向量
3. **存储**: 向量和元数据存储到pgvector数据库
4. **检索**: 用户查询生成向量，检索Top-K相关文档
5. **重排序**: 使用Qwen3-Reranker重新排序，选出Top-N
6. **生成**: 将上下文注入Qwen3-LLM生成最终答案

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <your-repo-url>
cd enterprise-rag

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 检查环境
python check_env.py
```

**系统依赖**：
- Python 3.8+
- PostgreSQL 12+ 
- Tesseract OCR（用于图片文字识别）

```bash
# Ubuntu/Debian 安装系统依赖
sudo apt-get update
sudo apt-get install python3-dev libpq-dev tesseract-ocr tesseract-ocr-chi-sim

# CentOS/RHEL
sudo yum install python3-devel postgresql-devel tesseract

# macOS
brew install postgresql tesseract tesseract-lang
```

### 2. 数据库配置

安装PostgreSQL和pgvector扩展：

```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
sudo apt-get install postgresql-14-pgvector

# 或使用Docker
docker run -d \
  --name postgres-pgvector \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=rag \
  -p 5432:5432 \
  pgvector/pgvector:pg14
```

### 3. 配置环境变量

```bash
# 复制环境变量模板（如果不存在）
cp .env .env.local

# 编辑配置文件
vim .env
```

**重要配置项说明**：
- `PG_PASSWORD`: 修改为安全的数据库密码
- `HF_ENDPOINT`: 国内用户建议使用 `https://hf-mirror.com` 加速模型下载
- `DEVICE`: 根据硬件选择 `auto`、`cpu` 或 `cuda`
- `MAX_MEMORY_GB`: 根据服务器内存调整

### 4. 初始化数据库

```bash
python init_db.py
```

### 5. 启动应用

```bash
# 方式1: 使用启动脚本
python run.py

# 方式2: 直接使用uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 6. 访问应用

- **Web界面**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/system/health

## 🐳 Docker部署

### 使用Docker Compose（推荐）

```bash
# 一键部署
./deploy.sh

# 或手动执行
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f rag-app
```

### 手动Docker部署

```bash
# 构建镜像
docker build -t enterprise-rag .

# 启动PostgreSQL
docker run -d \
  --name postgres-pgvector \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=rag \
  -p 5432:5432 \
  pgvector/pgvector:pg14

# 启动应用
docker run -d \
  --name rag-app \
  --link postgres-pgvector:postgres \
  -e PG_HOST=postgres \
  -p 8000:8000 \
  -v ./models:/app/models \
  enterprise-rag
```

## 📖 使用指南

### 导入文档

```bash
# 通过API导入
curl -X POST "http://localhost:8000/documents/import" \
  -H "Content-Type: application/json" \
  -d '{"directory": "/path/to/your/documents"}'

# 增量同步
curl -X POST "http://localhost:8000/documents/sync" \
  -H "Content-Type: application/json" \
  -d '{"directory": "/path/to/your/documents"}'
```

### 智能问答

```bash
curl -X POST "http://localhost:8000/qa" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "你的问题",
    "history": [["用户问题1", "助手回答1"]]
  }'
```

### 文档管理

```bash
# 获取文档列表
curl "http://localhost:8000/documents"

# 搜索文档
curl "http://localhost:8000/documents?search=关键词"

# 删除文档
curl -X DELETE "http://localhost:8000/documents/{document_id}"
```

## ⚙️ 配置说明

### 环境变量配置

| 变量名            | 默认值                    | 说明               |
| ----------------- | ------------------------- | ------------------ |
| `PG_HOST`         | localhost                 | PostgreSQL主机地址 |
| `PG_PORT`         | 5432                      | PostgreSQL端口     |
| `PG_USER`         | postgres                  | 数据库用户名       |
| `PG_PASSWORD`     | postgres                  | 数据库密码         |
| `PG_DB`           | rag                       | 数据库名           |
| `EMBEDDING_MODEL` | Qwen/Qwen3-Embedding-0.6B | 向量化模型         |
| `RERANK_MODEL`    | Qwen/Qwen3-Reranker-0.6B  | 重排序模型         |
| `LLM_MODEL`       | Qwen/Qwen3-0.6B           | 生成模型           |
| `CHUNK_SIZE`      | 400                       | 文档分块大小       |
| `CHUNK_OVERLAP`   | 100                       | 分块重叠大小       |
| `TOP_K`           | 10                        | 检索召回数量       |
| `TOP_N`           | 5                         | 重排序后数量       |

### 支持的文档格式

- **文本文件**: .txt, .md
- **办公文档**: .docx, .xlsx
- **PDF文档**: .pdf
- **图片文件**: .png, .jpg, .jpeg (通过OCR)

## 🔧 开发指南

### 项目结构

```
enterprise-rag/
├── main.py              # 主应用入口
├── config.py            # 配置管理
├── db.py               # 数据库连接
├── models.py           # 数据模型
├── embedding.py        # 向量化模块
├── rerank.py          # 重排序模块
├── llm.py             # 语言模型模块
├── document_loader.py  # 文档加载器
├── utils.py           # 工具函数
├── run.py             # 启动脚本
├── init_db.py         # 数据库初始化
├── check_env.py       # 环境检查
├── requirements.txt   # 依赖列表
├── .env              # 环境变量配置
├── docker-compose.yml # Docker编排文件
├── Dockerfile        # Docker镜像构建文件
├── deploy.sh         # 部署脚本
├── api/             # API路由模块
│   ├── __init__.py
│   └── routes/      # 路由定义
│       ├── __init__.py
│       ├── documents.py  # 文档管理接口
│       ├── qa.py        # 问答接口
│       └── system.py    # 系统接口
├── services/        # 业务服务层
│   ├── __init__.py
│   ├── document_service.py  # 文档处理服务
│   ├── import_service.py    # 导入服务
│   ├── qa_service.py        # 问答服务
│   └── system_service.py    # 系统服务
├── models/          # 数据模型目录
├── static/          # 静态文件
│   └── index.html   # Web界面
├── .cursor/         # Cursor编辑器配置
├── .kiro/          # Kiro AI助手配置
├── .vscode/        # VSCode配置
└── README.md       # 项目文档
```

### API接口

| 接口                     | 方法   | 说明     |
| ------------------------ | ------ | -------- |
| `/`                      | GET    | Web界面  |
| `/system/health`         | GET    | 健康检查 |
| `/system/stats`          | GET    | 系统统计 |
| `/system/info`           | GET    | 系统信息 |
| `/system/model_status`   | GET    | 模型状态 |
| `/documents/import`      | POST   | 导入目录 |
| `/documents/sync`        | POST   | 增量同步 |
| `/documents`             | GET    | 文档列表 |
| `/documents/{id}`        | DELETE | 删除文档 |
| `/documents/{id}/chunks` | GET    | 文档分块 |
| `/documents/clear_all`   | POST   | 清空文档 |
| `/qa`                    | POST   | 智能问答 |
| `/qa/batch`              | POST   | 批量问答 |
| `/qa/search`             | GET    | 内容搜索 |

## 🐛 故障排除

### 常见问题

1. **模型下载慢**
   ```bash
   # 设置HuggingFace镜像
   export HF_ENDPOINT=https://hf-mirror.com
   ```

2. **内存不足**
   ```bash
   # 调整模型配置
   export MAX_MEMORY_GB=4
   export DEVICE=cpu
   ```

3. **数据库连接失败**
   ```bash
   # 检查PostgreSQL服务
   sudo systemctl status postgresql
   
   # 检查pgvector扩展
   psql -d rag -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

### 日志查看

```bash
# 查看应用日志
tail -f rag_app.log

# 查看详细错误
python run.py --log-level debug

# Docker环境查看日志
docker-compose logs -f rag-app

# 实时监控系统状态
curl http://localhost:8000/system/stats
```

### 性能监控

应用提供了丰富的监控接口：

```bash
# 系统健康状态
curl http://localhost:8000/system/health

# 详细系统信息（CPU、内存、磁盘）
curl http://localhost:8000/system/info

# 模型加载状态
curl http://localhost:8000/system/model_status

# 文档统计信息
curl http://localhost:8000/system/stats
```

## 📊 性能优化

### 硬件建议

- **CPU**: 8核心以上
- **内存**: 16GB以上
- **GPU**: 支持CUDA的显卡（可选）
- **存储**: SSD硬盘

### 配置优化

```bash
# 批量处理优化
export MAX_BATCH_SIZE=20

# 向量索引优化
export HNSW_M=16
export HNSW_EF_CONSTRUCTION=200
```

## 🤝 贡献指南

1. Fork项目
2. 创建特性分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 📄 许可证

本项目采用MIT许可证 - 查看[LICENSE](LICENSE)文件了解详情。

## 🙏 致谢

- [Qwen团队](https://github.com/QwenLM/Qwen) - 提供优秀的开源模型
- [pgvector](https://github.com/pgvector/pgvector) - PostgreSQL向量扩展
- [LangChain](https://github.com/langchain-ai/langchain) - 文档处理工具

## 📞 支持

如有问题或建议，请提交Issue或联系维护者。