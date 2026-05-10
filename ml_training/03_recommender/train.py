"""
Обучение модели рекомендаций (GradientBoosting classifier).
Фичи совпадают с recommender.py FeatureExtractor.
"""
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

EXPENSE_CATEGORIES = [
    "groceries", "restaurants", "transport", "subscriptions",
    "shopping", "utilities", "health", "entertainment", "education",
]


class FeatureExtractor:
    """Должен совпадать с recommender.py FeatureExtractor"""

    def extract(self, transactions):
        df = pd.DataFrame(transactions)
        if "weekend" not in df.columns:
            df["weekend"] = 0
        if "merchant" not in df.columns:
            df["merchant"] = ""

        exp = df[df["type"] == "expense"]
        inc = df[df["type"] == "income"]
        f = {}

        ti = inc["amount"].sum() if not inc.empty else 0
        te = exp["amount"].sum() if not exp.empty else 1

        f["total_income"] = ti
        f["total_expenses"] = te
        f["savings_rate"] = (ti - te) / ti if ti > 0 else 0
        f["expense_to_income_ratio"] = te / ti if ti > 0 else 1
        f["weekend_spend_ratio"] = (
            exp[exp["weekend"] == 1]["amount"].sum() / te if te > 0 else 0
        )

        for cat in EXPENSE_CATEGORIES:
            ce = exp[exp["category"] == cat]
            f[f"total_{cat}"] = ce["amount"].sum()
            f[f"count_{cat}"] = len(ce)
            f[f"avg_{cat}"] = ce["amount"].mean() if not ce.empty else 0
            f[f"share_{cat}"] = f[f"total_{cat}"] / te if te > 0 else 0
            f[f"std_{cat}"] = ce["amount"].std() if len(ce) > 1 else 0

        if not exp.empty:
            f["num_transactions"] = len(exp)
            f["avg_transaction"] = exp["amount"].mean()
            f["max_transaction"] = exp["amount"].max()
            f["unique_merchants"] = (
                exp["merchant"].nunique() if "merchant" in exp.columns else 0
            )
        else:
            for k in [
                "num_transactions", "avg_transaction",
                "max_transaction", "unique_merchants",
            ]:
                f[k] = 0

        f["impulse_ratio"] = (
            f["max_transaction"] / f["avg_transaction"]
            if f["avg_transaction"] > 0 else 0
        )
        f["daily_frequency"] = f["num_transactions"] / 30
        f["food_total"] = f["total_groceries"] + f["total_restaurants"]
        f["food_share"] = f["food_total"] / te if te > 0 else 0
        f["leisure_total"] = (
            f["total_restaurants"] + f["total_entertainment"] + f["total_shopping"]
        )
        f["leisure_share"] = f["leisure_total"] / te if te > 0 else 0

        return f


def train():
    data_path = os.path.join(BASE_DIR, "data", "dataset.json")
    print(f"📂 Загрузка {data_path}...")
    with open(data_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    fe = FeatureExtractor()
    X_list, y_list, rec_map = [], [], {}

    print("🛠 Извлечение признаков...")
    for sample in tqdm(dataset):
        features = fe.extract(sample["transactions"])
        X_list.append(features)

        profile = sample["profile"]
        y_list.append(profile)

        # Сохраняем рекомендации для каждого профиля
        if profile not in rec_map:
            rec_map[profile] = sample["recommendations"]

    X = pd.DataFrame(X_list).fillna(0).replace([np.inf, -np.inf], 0)
    feature_names = list(X.columns)

    le = LabelEncoder()
    y = le.fit_transform(y_list)

    print(f"\n📊 Фичей: {len(feature_names)}")
    print(f"   Профилей: {len(le.classes_)}")
    print(f"   Сэмплов: {len(X)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42, stratify=y
    )

    print(f"\n🧠 Обучение GBM (n_estimators=300)...")
    model = GradientBoostingClassifier(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        min_samples_leaf=10,
        random_state=42,
        verbose=1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    print(f"\n{'🏆' * 20}")
    print(f"ТОЧНОСТЬ: {acc:.4f}")
    print(f"{'🏆' * 20}")
    print(f"\n{classification_report(y_test, y_pred, target_names=le.classes_)}")

    # Важность фичей
    importances = sorted(
        zip(feature_names, model.feature_importances_),
        key=lambda x: x[1], reverse=True,
    )
    print("📈 Топ-10 фичей:")
    for name, imp in importances[:10]:
        print(f"   {name}: {imp:.4f}")

    # Сохранение
    save_path = os.path.join(
        PROJECT_DIR, "backend", "app", "ml", "trained_models", "recommender"
    )
    os.makedirs(save_path, exist_ok=True)
    joblib.dump(model, os.path.join(save_path, "classifier.joblib"))
    joblib.dump(le, os.path.join(save_path, "label_encoder.joblib"))
    joblib.dump(feature_names, os.path.join(save_path, "feature_names.joblib"))
    with open(os.path.join(save_path, "recommendations_map.json"), "w", encoding="utf-8") as f:
        json.dump(rec_map, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Модель сохранена в {save_path}")


if __name__ == "__main__":
    train()