import os
import json
import logging
import joblib

logger = logging.getLogger(__name__)

class CategorizerModel:
    def __init__(self):
        self.model = None
        self.categories = {}
        self.type = None

    def load(self, model_path):
        # Логика загрузки (TF-IDF или RuBERT)
        if (model_path / "model.joblib").exists():
            self.model = joblib.load(model_path / "model.joblib")
            self.categories = json.load(open(model_path / "categories.json", encoding="utf-8"))
            self.type = "tfidf"
        # Тут можно добавить логику для RuBERT

    def predict(self, text):
        if not self.model:
            return {"category_code": "other", "confidence": 0.5}
        
        pred = self.model.predict([text.lower()])[0]
        probs = self.model.predict_proba([text.lower()])[0]
        return {
            "category_code": pred,
            "category_name": self.categories.get(pred, pred),
            "confidence": float(max(probs))
        }
