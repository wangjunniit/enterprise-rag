from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
from config import LLM_MODEL, DEVICE, MODEL_CACHE_DIR, LLM_INPUT_MAX_LENGTH, LLM_OUTPUT_MAX_LENGTH, LLM_TEMPERATURE, HF_ENDPOINT

class LLMModel:
    def __init__(self, model_name=None):
        if model_name is None:
            model_name = LLM_MODEL
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
        
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map=DEVICE if DEVICE != "auto" else "auto",
            max_memory=max_memory,
            cache_dir=MODEL_CACHE_DIR,
            mirror=HF_ENDPOINT if HF_ENDPOINT != 'https://huggingface.co' else None
        )
        self.model.eval()
        
        # 设置pad_token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
    
    def generate_answer(self, prompt: str, max_length=None, temperature=None):
        """生成回答"""
        # 使用配置中的默认值
        from config import LLM_INPUT_MAX_LENGTH, LLM_OUTPUT_MAX_LENGTH, LLM_TEMPERATURE
        if max_length is None:
            max_length = LLM_OUTPUT_MAX_LENGTH
        if temperature is None:
            temperature = LLM_TEMPERATURE
            
        # 构造对话格式
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        # 应用聊天模板
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # 编码输入
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            truncation=True,
            max_length=LLM_INPUT_MAX_LENGTH
        )
        
        # 生成回答
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_length - inputs['input_ids'].shape[1],
                temperature=temperature,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )
        
        # 解码输出
        response = self.tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        )
        
        return response.strip()

# 全局模型实例
_llm_model = None

def get_llm_model():
    global _llm_model
    if _llm_model is None:
        _llm_model = LLMModel()
    return _llm_model

def generate_answer(prompt: str):
    """生成回答"""
    model = get_llm_model()
    return model.generate_answer(prompt) 