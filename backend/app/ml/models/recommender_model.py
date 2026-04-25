import json
import joblib
import pandas as pd
import numpy as np
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class FeatureExtractor:
    EXPENSE_CATEGORIES = ["groceries", "restaurants", "transport", "subscriptions", "shopping", "utilities", "health", "entertainment", "education"]
    
    def extract(self, transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not transactions:
            return {f"share_{c}": 0 for c in self.EXPENSE_CATEGORIES} | {"total_income": 0, "total_expenses": 0}
            
        df = pd.DataFrame(transactions)
        # Приводим типы
        df["amount"] = df["amount"].apply(lambda x: float(x))
        
        expenses = df[df["amount"] < 0]
        income = df[df["amount"] > 0]
        
        total_income = float(income["amount"].sum()) if not income.empty else 0
        total_expenses = float(abs(expenses["amount"].sum())) if not expenses.empty else 1
        
        features = {"total_income": total_income, "total_expenses": total_expenses}
        for cat in self.EXPENSE_CATEGORIES:
            # Бэкенд может присылать разные коды категорий, нормализуем
            cat_tx = expenses[expenses["category_code"].str.lower() == cat.lower()] if "category_code" in expenses else expenses[expenses["category"] == cat]
            cat_sum = float(abs(cat_tx["amount"].sum())) if not cat_tx.empty else 0
            features[f"share_{cat}"] = cat_sum / total_expenses
            
        return features

class RecommenderModel:
    def __init__(self):
        self.model = None
        self.le = None
        self.features = None
        self.recs_map = {}
        self.extractor = FeatureExtractor()

    def load(self, path):
        if (path / "classifier.joblib").exists():
            try:
                self.model = joblib.load(path / "classifier.joblib")
                self.le = joblib.load(path / "label_encoder.joblib")
                self.features = joblib.load(path / "feature_names.joblib")
                with open(path / "recommendations_map.json", "r", encoding="utf-8") as f:
                    self.recs_map = json.load(f)
                logger.info("✅ Модель рекомендателя успешно загружена")
            except Exception as e:
                logger.error(f"Ошибка загрузки рекомендателя: {e}")

    def get_tips(self, transactions: List[Any]) -> List[Dict[str, Any]]:
        if not self.model or not transactions:
            return [{
                "id": 1, 
                "title": "Начните учёт трат", 
                "description": "Добавьте больше транзакций, чтобы ИИ смог проанализировать ваши привычки.", 
                "potential_savings": 0,
                "category": "general",
                "priority": "low"
            }]

        # Подготавливаем данные
        tx_dicts = []
        for t in transactions:
            tx_dicts.append({
                "amount": float(t.amount),
                "category": t.category.code if t.category else "other",
                "type": "income" if t.amount > 0 else "expense"
            })
            
        features = self.extractor.extract(tx_dicts)
        X = pd.DataFrame([features])[self.features]
        
        # Предсказание профиля
        pred_idx = self.model.predict(X)[0]
        profile_label = self.le.inverse_transform([pred_idx])[0]
        
        # Получаем советы для этого профиля
        base_recs = self.recs_map.get(profile_label, [])
        
        result = []
        for i, r in enumerate(base_recs):
            result.append({
                "id": 200 + i,
                "title": r["title"],
                "description": r["description"],
                "potential_savings": r["potential_savings"],
                "category": r.get("category", "general"),
                "priority": "high" if r["potential_savings"] > 2000 else "medium"
            })
            
        return result
