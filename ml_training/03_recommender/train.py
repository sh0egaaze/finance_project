import pandas as pd
import numpy as np
import json
import os
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score

# Настройка путей
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))

class FeatureExtractor:
    EXPENSE_CATEGORIES = ["groceries", "restaurants", "transport", "subscriptions", "shopping", "utilities", "health", "entertainment", "education"]
    
    def extract(self, transactions: list[dict]) -> dict:
        df = pd.DataFrame(transactions)
        exp = df[df["type"] == "expense"]
        inc = df[df["type"] == "income"]
        f = {}
        ti = inc["amount"].sum() if not inc.empty else 0
        te = exp["amount"].sum() if not exp.empty else 0
        f["total_income"], f["total_expenses"] = ti, te
        f["savings_rate"] = (ti - te) / ti if ti > 0 else 0
        f["expense_to_income_ratio"] = te / ti if ti > 0 else 1
        
        for cat in self.EXPENSE_CATEGORIES:
            ce = exp[exp["category"] == cat]
            f[f"total_{cat}"] = ce["amount"].sum()
            f[f"count_{cat}"] = len(ce)
            f[f"avg_{cat}"] = ce["amount"].mean() if not ce.empty else 0
            f[f"share_{cat}"] = f[f"total_{cat}"] / te if te > 0 else 0
        
        if not exp.empty:
            f["num_transactions"] = len(exp)
            f["avg_transaction"] = exp["amount"].mean()
            f["max_transaction"] = exp["amount"].max()
            f["unique_merchants"] = exp["merchant"].nunique()
        else:
            for k in ["num_transactions", "avg_transaction", "max_transaction", "unique_merchants"]: f[k] = 0
            
        f["impulse_ratio"] = f["max_transaction"] / f["avg_transaction"] if f["avg_transaction"] > 0 else 0
        f["daily_frequency"] = f["num_transactions"] / 30
        
        # Соотношения
        f["food_total"] = f["total_groceries"] + f["total_restaurants"]
        f["food_share"] = f["food_total"] / te if te > 0 else 0
        f["leisure_total"] = f["total_restaurants"] + f["total_entertainment"] + f["total_shopping"]
        f["leisure_share"] = f["leisure_total"] / te if te > 0 else 0
        
        return f

def train():
    data_path = os.path.join(BASE_DIR, "data", "dataset.json")
    with open(data_path, "r", encoding="utf-8") as f: dataset = json.load(f)
    
    fe = FeatureExtractor()
    X_list, y_labels, rec_map = [], [], {}
    
    for sample in dataset:
        X_list.append(fe.extract(sample["transactions"]))
        label = sample["recommendations"][0]["title"]
        y_labels.append(label)
        if label not in rec_map: rec_map[label] = sample["recommendations"]
    
    X = pd.DataFrame(X_list).fillna(0).replace([np.inf, -np.inf], 0)
    le = LabelEncoder()
    y = le.fit_transform(y_labels)
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    model = RandomForestClassifier(n_estimators=200, max_depth=20, random_state=42)
    model.fit(X_train, y_train)
    
    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"✅ Модель обучена. Accuracy: {acc:.4f}")
    
    # Сохранение в бэкенд
    save_path = os.path.join(PROJECT_DIR, "backend", "app", "ml", "trained_models", "recommender")
    os.makedirs(save_path, exist_ok=True)
    joblib.dump(model, os.path.join(save_path, "classifier.joblib"))
    joblib.dump(le, os.path.join(save_path, "label_encoder.joblib"))
    joblib.dump(list(X.columns), os.path.join(save_path, "feature_names.joblib"))
    with open(os.path.join(save_path, "recommendations_map.json"), "w", encoding="utf-8") as f:
        json.dump(rec_map, f, ensure_ascii=False, indent=2)
    print(f"✅ Артефакты сохранены в {save_path}")

if __name__ == "__main__":
    train()
