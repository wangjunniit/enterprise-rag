import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

from config import RERANK_MODEL, DEVICE, MODEL_CACHE_DIR, RERANK_MAX_LENGTH, HF_ENDPOINT


class RerankModel:
    def __init__(self, model_name=None):
        if model_name is None:
            model_name = RERANK_MODEL
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
        
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name, 
            torch_dtype=torch.float16, 
            device_map=DEVICE if DEVICE != "auto" else "auto",
            max_memory=max_memory,
            cache_dir=MODEL_CACHE_DIR,
            mirror=HF_ENDPOINT if HF_ENDPOINT != 'https://huggingface.co' else None
        )
        self.model.eval()
    
    def compute_score(self, query: str, passage: str):
        """计算query和passage的相关性分数"""
        inputs = self.tokenizer(
            query, passage, 
            return_tensors="pt", 
            truncation=True, 
            max_length=RERANK_MAX_LENGTH,
            padding=True
        )
        with torch.no_grad():
            outputs = self.model(**inputs)
            score = torch.sigmoid(outputs.logits)[:, 1].item()
            return score
    
    def rerank(self, query: str, docs: list):
        """对文档进行重排序"""
        scored_docs = []
        for doc in docs:
            score = self.compute_score(query, doc['content'])
            scored_docs.append({
                'content': doc['content'],
                'meta': doc['meta'],
                'score': score
            })
        
        # 按分数降序排列
        scored_docs.sort(key=lambda x: x['score'], reverse=True)
        return scored_docs

# 全局模型实例
_rerank_model = None

def get_rerank_model():
    global _rerank_model
    if _rerank_model is None:
        _rerank_model = RerankModel()
    return _rerank_model

def rerank(query: str, docs: list):
    """重排序文档"""
    model = get_rerank_model()
    return model.rerank(query, docs) 