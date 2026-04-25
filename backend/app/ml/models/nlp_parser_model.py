import os
import torch
import math
import re
from transformers import AutoTokenizer
from .nlp_architecture import FinanceNLPModel

class NLPParserModel:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.loaded = False

    def load(self, path):
        weights = path / "weights.pt"
        if weights.exists():
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(str(path / "tokenizer"))
                self.model = FinanceNLPModel()
                self.model.load_state_dict(torch.load(str(weights), map_location="cpu"))
                self.model.eval()
                self.loaded = True
            except Exception as e:
                print(f"Ошибка загрузки NLP: {e}")

    def parse(self, text: str):
        if not self.loaded:
            # Fallback на регулярки
            amt_match = re.search(r'(\d+)', text)
            amount = float(amt_match.group(1)) if amt_match else 0.0
            return {"amount": amount, "description": text, "is_income": False}
        
        # Здесь будет реальный инференс BERT
        return {"amount": 0.0, "description": text, "is_income": False}
