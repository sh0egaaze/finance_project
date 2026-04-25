from dataclasses import dataclass, field
from typing import List, Dict, Any
import logging
import re

logger = logging.getLogger(__name__)

@dataclass
class CategoryPrediction:
    category_code: str
    category_name: str
    confidence: float
    method: str
    top_3: List[dict] = field(default_factory=list)

    def to_dict(self):
        return {
            "category_code": self.category_code,
            "category_name": self.category_name,
            "confidence": self.confidence,
            "method": self.method,
            "top_3": self.top_3
        }

def categorize(description: str) -> CategoryPrediction:
    from .model_loader import registry
    model_data = registry.get("categorizer")
    
    if not model_data:
        return _fallback(description)

    desc = description.lower().strip()
    
    if model_data["type"] == "rubert":
        import torch
        model, tokenizer, id2cat = model_data["model"], model_data["tokenizer"], model_data["id2cat"]
        inputs = tokenizer(desc, return_tensors="pt", truncation=True, max_length=64)
        with torch.no_grad():
            logits = model(**inputs).logits
            probs = torch.softmax(logits, dim=-1)[0]
            conf, pred_id = torch.max(probs, dim=-1)
        code = id2cat[str(pred_id.item())]
        return CategoryPrediction(code, code, float(conf.item()), "rubert")

    if model_data["type"] == "tfidf":
        model, cats = model_data["model"], model_data["categories"]
        pred = model.predict([desc])[0]
        conf = float(max(model.predict_proba([desc])[0]))
        return CategoryPrediction(pred, cats.get(pred, pred), conf, "tfidf")

    return _fallback(description)

def _fallback(text):
    # Упрощенные правила
    rules = [("food", "Еда", ["еда", "кофе"]), ("transport", "Транспорт", ["такси", "метро"])]
    for code, name, kws in rules:
        if any(k in text.lower() for k in kws):
            return CategoryPrediction(code, name, 0.6, "fallback")
    return CategoryPrediction("other", "Прочее", 0.3, "fallback")
