import pandas as pd
import numpy as np
import json
import os
import joblib
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
from tqdm import tqdm

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(os.path.dirname(BASE_DIR))

class FeatureExtractor:
    EXPENSE_CATEGORIES = ["groceries", "restaurants", "transport", "subscriptions", "shopping", "utilities", "health", "entertainment", "education"]
    
    def extract(self, transactions):
        df = pd.DataFrame(transactions)
        exp = df[df["type"] == "expense"]
        inc = df[df["type"] == "income"]
        f = {}
        ti = inc["amount"].sum() if not inc.empty else 0
        te = exp["amount"].sum() if not exp.empty else 1
        
        f["total_income"] = ti
        f["total_expenses"] = te
        f["savings_rate"] = (ti - te) / ti if ti > 0 else 0
        
        # Сложные признаки
        f["weekend_spend_ratio"] = exp[exp["weekend"] == 1]["amount"].sum() / te if te > 0 else 0
        
        for cat in self.EXPENSE_CATEGORIES:
            ce = exp[exp["category"] == cat]
            f[f"share_{cat}"] = ce["amount"].sum() / te
            f[f"count_{cat}"] = len(ce)
            f[f"std_{cat}"] = ce["amount"].std() if len(ce) > 1 else 0
        
        return f

def train():
    print("📂 Загрузка 100,000 сэмплов...")
    # ИСПРАВЛЕНО: Добавлена кодировка utf-8
    data_path = os.path.join(BASE_DIR, "data", "dataset.json")
    with open(data_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)
    
    fe = FeatureExtractor()
    X_list, y_list, rec_map = [], [], {}
    
    print("🛠 Масштабное извлечение признаков (это займет пару минут)...")
    for sample in tqdm(dataset):
        X_list.append(fe.extract(sample["transactions"]))
        title = sample["recommendations"][0]["title"]
        y_list.append(title)
        rec_map[title] = sample["recommendations"]

    X = pd.DataFrame(X_list).fillna(0)
    le = LabelEncoder()
    y = le.fit_transform(y_list)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42, stratify=y)

    print(f"🧠 Обучение тяжелого бустинга (n_estimators=250)...")
    model = GradientBoostingClassifier(
        n_estimators=250, 
        learning_rate=0.05, 
        max_depth=6, 
        subsample=0.8,
        random_state=42,
        verbose=1 
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    
    print("\n" + "🏆" * 20)
    print(f"ИТОГОВАЯ ТОЧНОСТЬ: {acc:.4f}")
    print("🏆" * 20)
    
    print("\n📊 Анализ по категориям советов:")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    # Сохранение в бэкенд
    save_path = os.path.join(PROJECT_DIR, "backend", "app", "ml", "trained_models", "recommender")
    os.makedirs(save_path, exist_ok=True)
    joblib.dump(model, os.path.join(save_path, "classifier.joblib"))
    joblib.dump(le, os.path.join(save_path, "label_encoder.joblib"))
    joblib.dump(list(X.columns), os.path.join(save_path, "feature_names.joblib"))
    with open(os.path.join(save_path, "recommendations_map.json"), "w", encoding="utf-8") as f:
        json.dump(rec_map, f, ensure_ascii=False, indent=2)
    print(f"\n💾 Все 100к знаний упакованы в {save_path}")

if __name__ == "__main__":
    train()