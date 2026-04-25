import os
import math
import torch
import re
from transformers import AutoTokenizer
from .model_definition import FinanceNLPModel

class FinanceParser:
    """
    Парсер финансовых транзакций (ПОЛНАЯ ВЕРСИЯ).
    """
    def __init__(self, model_dir: str):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        checkpoint_path = os.path.join(model_dir, "checkpoint.pt")
        tokenizer_path = os.path.join(model_dir, "tokenizer")
        
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)
        checkpoint = torch.load(checkpoint_path, map_location=self.device, weights_only=False)
        
        conf = checkpoint["config"]
        self.model = FinanceNLPModel(conf["pretrained_model_name"], conf["num_bio_labels"])
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.model.eval()
        
        self.max_length = conf["max_seq_length"]
        self.bio_labels = {0: "O", 1: "B-DESC", 2: "I-DESC"}

    def _extract_description_from_bio(self, tokens, bio_preds, attention_mask):
        description_tokens = []
        in_description = False
        for i, (token, bio, mask) in enumerate(zip(tokens, bio_preds, attention_mask)):
            if mask == 0: break
            if bio == 1: # B-DESC
                in_description = True
                description_tokens.append(token)
            elif bio == 2 and in_description: # I-DESC
                description_tokens.append(token)
            else:
                if in_description: break
        
        if not description_tokens: return ""
        text = self.tokenizer.convert_tokens_to_string(description_tokens)
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        return text

    def parse(self, text: str) -> dict:
        encoding = self.tokenizer(text, max_length=self.max_length, padding="max_length", truncation=True, return_tensors="pt")
        input_ids = encoding["input_ids"].to(self.device)
        attention_mask = encoding["attention_mask"].to(self.device)
        
        with torch.no_grad():
            amount_pred, income_logits, bio_logits = self.model(input_ids, attention_mask)
        
        log_amount = amount_pred.squeeze().item()
        amount = round(math.exp(log_amount), 2)
        
        income_probs = torch.softmax(income_logits, dim=-1).squeeze()
        is_income = income_probs[1].item() > 0.5
        
        bio_preds = bio_logits.argmax(dim=-1).squeeze().cpu().tolist()
        tokens = self.tokenizer.convert_ids_to_tokens(input_ids.squeeze().cpu().tolist())
        att_mask = attention_mask.squeeze().cpu().tolist()
        
        description = self._extract_description_from_bio(tokens, bio_preds, att_mask)
        
        return {
            "amount": float(amount),
            "description": description or text,
            "is_income": bool(is_income),
            "confidence": {
                "income_confidence": round(float(income_probs[1 if is_income else 0].item()), 4),
                "amount_log": round(log_amount, 4)
            }
        }

def parse_text(text: str) -> dict:
    from .model_loader import registry
    parser = registry.get("nlp_parser")
    if not parser:
        return {"amount": 0, "description": text, "is_income": False, "error": "Model not loaded"}
    return parser.parse(text)
