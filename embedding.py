from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from config import EMBEDDING_MODEL, DEVICE, MODEL_CACHE_DIR, EMBEDDING_MAX_LENGTH, HF_ENDPOINT

class EmbeddingModel:
    def __init__(self, model_name=None):
        if model_name is None:
            model_name = EMBEDDING_MODEL
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_name, 
            cache_dir=MODEL_CACHE_DIR,
            mirror=HF_ENDPOINT if HF_ENDPOINT != 'https://huggingface.co' else None
        )
        # 配置内存限制
        max_memory = None
        if DEVICE == "auto":
            from config import MAX_MEMORY_GB
            max_memory = {0: f"{MAX_MEMORY_GB}GB"} if torch.cuda.is_available() else None
        
        self.model = AutoModel.from_pretrained(
            model_name, 
            torch_dtype=torch.float16, 
            device_map=DEVICE if DEVICE != "auto" else "auto",
            max_memory=max_memory,
            cache_dir=MODEL_CACHE_DIR,
            mirror=HF_ENDPOINT if HF_ENDPOINT != 'https://huggingface.co' else None
        )
        self.model.eval()
    
    def get_embedding(self, text: str):
        """获取文本的向量表示"""
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=EMBEDDING_MAX_LENGTH)
        with torch.no_grad():
            outputs = self.model(**inputs)
            # 使用CLS token的输出或者平均池化
            embeddings = outputs.last_hidden_state.mean(dim=1)
            return embeddings.cpu().numpy().flatten().tolist()

# 全局模型实例
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model

def get_embedding(text: str):
    """获取文本向量"""
    model = get_embedding_model()
    return model.get_embedding(text) 