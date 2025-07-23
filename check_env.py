#!/usr/bin/env python3
"""
环境检查脚本 - 检查依赖和配置
"""
import importlib
import os
import sys
from pathlib import Path


def check_python_version():
    """检查Python版本"""
    print("🐍 检查Python版本...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python版本过低: {version.major}.{version.minor}")
        print("   需要Python 3.8或更高版本")
        return False
    print(f"✅ Python版本: {version.major}.{version.minor}.{version.micro}")
    return True

def check_dependencies():
    """检查依赖包"""
    print("\n📦 检查依赖包...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'sqlalchemy',
        'psycopg2',
        'torch',
        'transformers',
        'langchain_community',
        'pandas',
        'PIL',
        'pytesseract'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - 未安装")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n❌ 缺少依赖包: {', '.join(missing_packages)}")
        print("请运行: pip install -r requirements.txt")
        return False
    
    return True

def check_database_config():
    """检查数据库配置"""
    print("\n🗄️ 检查数据库配置...")
    
    required_env_vars = [
        'PG_HOST',
        'PG_PORT', 
        'PG_USER',
        'PG_PASSWORD',
        'PG_DB'
    ]
    
    missing_vars = []
    for var in required_env_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️ 缺少环境变量: {', '.join(missing_vars)}")
        print("将使用默认配置")
    else:
        print("✅ 数据库环境变量配置完整")
    
    return True

def check_model_config():
    """检查模型配置"""
    print("\n🤖 检查模型配置...")
    
    model_vars = [
        ('EMBEDDING_MODEL', 'Qwen/Qwen3-Embedding-0.6B'),
        ('RERANK_MODEL', 'Qwen/Qwen3-Reranker-0.6B'),
        ('LLM_MODEL', 'Qwen/Qwen3-0.6B')
    ]
    
    for var, default in model_vars:
        value = os.getenv(var, default)
        print(f"✅ {var}: {value}")
    
    return True

def check_directories():
    """检查必要的目录"""
    print("\n📁 检查目录结构...")
    
    required_dirs = [
        'static',
        'models'  # 模型缓存目录
    ]
    
    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            print(f"⚠️ 目录不存在，正在创建: {dir_name}")
            dir_path.mkdir(exist_ok=True)
        print(f"✅ {dir_name}/")
    
    return True

def check_gpu():
    """检查GPU可用性"""
    print("\n🖥️ 检查GPU...")
    
    try:
        import torch
        if torch.cuda.is_available():
            gpu_count = torch.cuda.device_count()
            gpu_name = torch.cuda.get_device_name(0)
            print(f"✅ GPU可用: {gpu_count}个设备")
            print(f"   主GPU: {gpu_name}")
            print(f"   CUDA版本: {torch.version.cuda}")
        else:
            print("⚠️ GPU不可用，将使用CPU")
            print("   注意: CPU运行速度较慢")
    except ImportError:
        print("❌ PyTorch未安装，无法检查GPU")
        return False
    
    return True

def main():
    """主检查函数"""
    print("🔍 企业RAG应用环境检查")
    print("=" * 50)
    
    checks = [
        check_python_version,
        check_dependencies,
        check_database_config,
        check_model_config,
        check_directories,
        check_gpu
    ]
    
    all_passed = True
    for check in checks:
        if not check():
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ 环境检查通过！可以启动应用")
        print("\n🚀 启动命令:")
        print("   python run.py")
        print("   或者: python -m uvicorn main:app --host 0.0.0.0 --port 8000")
    else:
        print("❌ 环境检查未通过，请修复上述问题")
        sys.exit(1)

if __name__ == "__main__":
    main()