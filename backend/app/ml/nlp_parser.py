import os
import torch
import math
import re
from transformers import AutoTokenizer
from .model_definition import FinanceNLPModel

class NLPParser:
    def __init__(self):
        self.device = torch.device("cpu")
        self.model_path = os.path.join(os.path.dirname(__file__), "trained_models/rubert_nlp/weights.pt")
        self.tok_path = os.path.join(os.path.dirname(__file__), "trained_models/rubert_nlp/tokenizer")
        
        if os.path.exists(self.model_path):
            self.tokenizer = AutoTokenizer.from_pretrained(self.tok_path)
            self.model = FinanceNLPModel("DeepPavlov/rubert-base-cased")
            self.model.load_state_dict(torch.load(self.model_path, map_location="cpu"))
            self.model.eval()
            self.loaded = True
        else:
            self.loaded = False

    def parse(self, text: str):
        if not self.loaded:
            # Fallback на регулярки если модель не обучена
            amt = re.search(r'(\d+)', text)
            return {"amount": float(amt.group(1)) if amt else 0, "description": text, "is_income": False}

        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=64)
        with torch.no_grad():
            p_amt, p_inc, p_bio = self.model(inputs["input_ids"], inputs["attention_mask"])
        
        amount = math.exp(p_amt.item())
        is_income = torch.argmax(p_inc, dim=-1).item() == 1
        
        # Извлекаем описание из BIO тегов
        tokens = self.tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
        bio_preds = torch.argmax(p_bio, dim=-1)[0].tolist()
        
        desc_tokens = []
        for i, (tok, pred) in enumerate(zip(tokens, bio_preds)):
            if pred in [1, 2]: # B-DESC или I-DESC
                desc_tokens.append(tok)
        
        description = self.tokenizer.convert_tokens_to_string(desc_tokens)
        return {
            "amount": round(amount, 2),
            "description": description or text,
            "is_income": is_income
        }
