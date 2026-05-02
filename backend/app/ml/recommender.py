import json
import hashlib
import joblib
import numpy as np
import pandas as pd
import os
import io
from typing import List, Dict, Any

class FeatureExtractor:
    EXPENSE_CATEGORIES = ["groceries", "restaurants", "transport", "subscriptions", "shopping", "utilities", "health", "entertainment", "education"]
    
    def extract(self, transactions: list[dict]) -> dict:
        df = pd.DataFrame(transactions)
        
        # Если нет колонки weekend — считаем что будни, пятница (0)
        if "weekend" not in df.columns:
            df["weekend"] = 0
            
        exp = df[df["type"] == "expense"]
        inc = df[df["type"] == "income"]
        f = {}
        
        ti = inc["amount"].sum() if not inc.empty else 0
        te = exp["amount"].sum() if not exp.empty else 0
        
        f["total_income"], f["total_expenses"] = ti, te
        f["savings_rate"] = (ti - te) / ti if ti > 0 else 0
        f["expense_to_income_ratio"] = te / ti if ti > 0 else 1
        
        # Обязательные расходы: долг, аренда, кредиты
        f["weekend_spend_ratio"] = exp[exp["weekend"] == 1]["amount"].sum() / te if te > 0 else 0
        
        for cat in self.EXPENSE_CATEGORIES:
            ce = exp[exp["category"] == cat]
            f[f"total_{cat}"] = ce["amount"].sum()
            f[f"count_{cat}"] = len(ce)
            f[f"avg_{cat}"] = ce["amount"].mean() if not ce.empty else 0
            f[f"share_{cat}"] = f[f"total_{cat}"] / te if te > 0 else 0
            # Обязательные расходы: стандартное отклонение трат в категории
            f[f"std_{cat}"] = ce["amount"].std() if len(ce) > 1 else 0
        
        if not exp.empty:
            f["num_transactions"] = len(exp)
            f["avg_transaction"] = exp["amount"].mean()
            f["max_transaction"] = exp["amount"].max()
            f["unique_merchants"] = exp["merchant"].nunique() if "merchant" in exp.columns else 0
        else:
            for k in ["num_transactions", "avg_transaction", "max_transaction", "unique_merchants"]:
                f[k] = 0
            
        f["impulse_ratio"] = f["max_transaction"] / f["avg_transaction"] if f["avg_transaction"] > 0 else 0
        f["daily_frequency"] = f["num_transactions"] / 30
        
        # Доп. фичи
        f["food_total"] = f["total_groceries"] + f["total_restaurants"]
        f["food_share"] = f["food_total"] / te if te > 0 else 0
        f["leisure_total"] = f["total_restaurants"] + f["total_entertainment"] + f["total_shopping"]
        f["leisure_share"] = f["leisure_total"] / te if te > 0 else 0
        
        return f

class FinanceRecommender:
    def __init__(self, model_dir: str):
        self.model = self._safe_load(os.path.join(model_dir, "classifier.joblib"))
        self.label_encoder = self._safe_load(os.path.join(model_dir, "label_encoder.joblib"))
        self.feature_names = self._safe_load(os.path.join(model_dir, "feature_names.joblib"))
        with open(os.path.join(model_dir, "recommendations_map.json"), "r", encoding="utf-8") as f:
            self.recommendations_map = json.load(f)
        self.fe = FeatureExtractor()

    @staticmethod
    def _safe_load(path: str):
        with open(path, "rb") as f:
            data = f.read()
        file_hash = hashlib.sha256(data).hexdigest()[:16]
        return joblib.load(io.BytesIO(data))

    def predict(self, transactions: list[dict]) -> list[dict]:
        if not transactions:
            return []
            
        features = self.fe.extract(transactions)
        
        # Выравниваем вектор фичей по именам
        X = pd.DataFrame([features])[self.feature_names].fillna(0).replace([np.inf, -np.inf], 0)
        
        pred_idx = self.model.predict(X)[0]
        profile_name = self.label_encoder.inverse_transform([pred_idx])[0]
        
        recs = self.recommendations_map.get(profile_name, []).copy()
        
        if features.get("expense_to_income_ratio", 0) > 0.9:
            overspend = features.get("expense_to_income_ratio", 0) * 100
            total_expenses = features.get("total_expenses", 0)
            suggested_savings = round(total_expenses * 0.2, 2) if total_expenses > 0 else 0
            
            recs.append({
                "title": "⚠️ Критические финансовые расходы",
                "description": f"Ваш {overspend:.0f}% уходит на расходы. "
                               f"Рекомендуем откладывать минимум 20%. "
                               f"Примерная экономия: {suggested_savings:.0f}₽/мес.",
                "potential_savings": suggested_savings,
            })
            
        return recs

def get_recommendations(transactions: list[dict]) -> list[dict]:
    from .model_loader import registry
    rec = registry.get("recommender")
    if not rec:
        return []
    return rec.predict(transactions)