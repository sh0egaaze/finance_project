import pandas as pd
import numpy as np
import json
import os
import joblib
from typing import List, Tuple
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.multioutput import MultiOutputClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, f1_score, hamming_loss, classification_report
from sklearn.preprocessing import StandardScaler
# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "trained_models", "recommender")
# Метки
LABELS = [
    "high_restaurants",
    "high_subscriptions",
    "high_shopping",
    "high_transport",
    "high_entertainment",
    "impulse_buyer",
    "low_savings",
    "weekend_spender",
]
# Категории
CATEGORIES = [
    "groceries", "restaurants", "transport", "subscriptions",
    "shopping", "utilities", "health", "entertainment", "education"
]
# Фичи БЕЗ share_* (чтобы избежать утечки)
FEATURE_COLUMNS = [
    # Базовые
    "total_income",
    "total_expenses",
    "savings_rate",
    "expense_to_income_ratio",
    
    # Транзакционные
    "num_transactions",
    "avg_transaction",
    "median_transaction",
    "max_transaction",
    "min_transaction",
    "std_transaction",
    "impulse_ratio",
    "cv_transaction",
    "unique_merchants",
    "unique_categories",
    "tx_per_category",
    
    # Weekend
    "weekend_total",
    "weekend_ratio",
    
    # Концентрация
    "top3_concentration",
    
    # По категориям (total, count, avg, max, ratio_income)
    *[f"total_{cat}" for cat in CATEGORIES],
    *[f"count_{cat}" for cat in CATEGORIES],
    *[f"avg_{cat}" for cat in CATEGORIES],
    *[f"max_{cat}" for cat in CATEGORIES],
    *[f"std_{cat}" for cat in CATEGORIES],
    *[f"ratio_income_{cat}" for cat in CATEGORIES],
]
def load_data() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Загружает данные"""
    features_path = os.path.join(DATA_DIR, "features.csv")
    labels_path = os.path.join(DATA_DIR, "labels.csv")
    
    if os.path.exists(features_path):
        print("📂 Загрузка CSV...")
        X = pd.read_csv(features_path)
        y = pd.read_csv(labels_path)
        return X, y
    
    # Fallback на JSON
    json_path = os.path.join(DATA_DIR, "dataset_v3.json")
    if os.path.exists(json_path):
        print("📂 Загрузка JSON...")
        with open(json_path, "r", encoding="utf-8") as f:
            dataset = json.load(f)
        X = pd.DataFrame([d["features"] for d in dataset])
        y = pd.DataFrame([d["labels"] for d in dataset])
        return X, y
    
    raise FileNotFoundError("Датасет не найден. Запустите generate_dataset.py")
def train():
    """Обучение модели"""
    print("=" * 70)
    print("🚀 ОБУЧЕНИЕ ГИБРИДНОЙ МОДЕЛИ v3.0")
    print("=" * 70)
    
    # 1. Загрузка
    X_raw, y_raw = load_data()
    
    # Фильтруем колонки
    available_features = [f for f in FEATURE_COLUMNS if f in X_raw.columns]
    available_labels = [l for l in LABELS if l in y_raw.columns]
    
    X = X_raw[available_features].fillna(0).replace([np.inf, -np.inf], 0)
    y = y_raw[available_labels]
    
    print(f"\n📊 Данные:")
    print(f"   Сэмплов:  {len(X):,}")
    print(f"   Фичей:    {len(available_features)}")
    print(f"   Меток:    {len(available_labels)}")
    
    # Проверка что нет share_* (утечки)
    leak_features = [f for f in available_features if f.startswith("share_")]
    if leak_features:
        print(f"\n⚠️  ВНИМАНИЕ: обнаружены share_* фичи: {leak_features}")
        print("   Это может привести к утечке данных!")
    else:
        print(f"\n   ✓ Утечка данных исключена (нет share_* фичей)")
    
    # 2. Разделение
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42
    )
    
    print(f"\n   Train: {len(X_train):,}")
    print(f"   Test:  {len(X_test):,}")
    
    # 3. Масштабирование
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # 4. Обучение
    print("\n🧠 Обучение (GradientBoosting x 8 меток)...")
    
    base_clf = GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.08,
        max_depth=6,
        subsample=0.8,
        min_samples_leaf=15,
        max_features="sqrt",
        random_state=42,
        verbose=0,
    )
    
    model = MultiOutputClassifier(base_clf, n_jobs=-1)
    model.fit(X_train_scaled, y_train)
    
    # 5. Оценка
    print("\n" + "=" * 70)
    print("📈 РЕЗУЛЬТАТЫ")
    print("=" * 70)
    
    y_pred = model.predict(X_test_scaled)
    
    # Метрики
    hamming = hamming_loss(y_test, y_pred)
    f1_micro = f1_score(y_test, y_pred, average="micro", zero_division=0)
    f1_macro = f1_score(y_test, y_pred, average="macro", zero_division=0)
    
    print(f"\n   Hamming Loss: {hamming:.4f} (идеал: 0)")
    print(f"   F1 Micro:     {f1_micro:.4f}")
    print(f"   F1 Macro:     {f1_macro:.4f}")
    
    # По меткам
    print("\n   Детализация по меткам:")
    print("   " + "-" * 65)
    print(f"   {'Метка':<25} | {'Acc':>6} | {'F1':>6} | {'Support':>7} | Качество")
    print("   " + "-" * 65)
    
    quality_scores = []
    for i, label in enumerate(available_labels):
        y_true_label = y_test.iloc[:, i]
        y_pred_label = y_pred[:, i]
        
        acc = accuracy_score(y_true_label, y_pred_label)
        f1 = f1_score(y_true_label, y_pred_label, zero_division=0)
        support = y_true_label.sum()
        
        quality = "🟢" if f1 >= 0.6 else "🟡" if f1 >= 0.4 else "🔴"
        quality_scores.append(f1)
        
        print(f"   {label:<25} | {acc:>6.3f} | {f1:>6.3f} | {support:>7} | {quality}")
    
    print("   " + "-" * 65)
    avg_quality = np.mean(quality_scores)
    overall = "🟢 Хорошо" if avg_quality >= 0.6 else "🟡 Средне" if avg_quality >= 0.4 else "🔴 Плохо"
    print(f"   {'СРЕДНЕЕ':<25} | {'':<6} | {avg_quality:>6.3f} | {'':<7} | {overall}")
    
    # 6. Важность фичей
    print("\n📊 Топ-15 важных фичей (усреднено по меткам):")
    
    # Усредняем важность по всем классификаторам
    all_importances = np.zeros(len(available_features))
    for estimator in model.estimators_:
        all_importances += estimator.feature_importances_
    all_importances /= len(model.estimators_)
    
    top_features = sorted(
        zip(available_features, all_importances),
        key=lambda x: x[1],
        reverse=True
    )[:15]
    
    max_imp = top_features[0][1] if top_features else 1
    for feat, imp in top_features:
        bar = "█" * int(imp / max_imp * 20)
        print(f"   {feat:<30} {bar} {imp:.4f}")
    
    # 7. Сохранение
    print("\n💾 Сохранение модели...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    joblib.dump(model, os.path.join(OUTPUT_DIR, "multilabel_model.joblib"))
    joblib.dump(scaler, os.path.join(OUTPUT_DIR, "scaler.joblib"))
    joblib.dump(available_features, os.path.join(OUTPUT_DIR, "feature_names.joblib"))
    joblib.dump(available_labels, os.path.join(OUTPUT_DIR, "label_names.joblib"))
    
    metadata = {
        "version": "3.0",
        "model_type": "MultiOutputClassifier(GradientBoostingClassifier)",
        "n_estimators": 200,
        "num_features": len(available_features),
        "num_labels": len(available_labels),
        "labels": available_labels,
        "metrics": {
            "hamming_loss": float(hamming),
            "f1_micro": float(f1_micro),
            "f1_macro": float(f1_macro),
            "per_label_f1": {label: float(quality_scores[i]) for i, label in enumerate(available_labels)},
        },
        "top_features": [{"name": f, "importance": float(i)} for f, i in top_features[:10]],
    }
    
    with open(os.path.join(OUTPUT_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Модель сохранена: {OUTPUT_DIR}")
    print("   - multilabel_model.joblib")
    print("   - scaler.joblib")
    print("   - feature_names.joblib")
    print("   - label_names.joblib")
    print("   - metadata.json")
    
    return model, scaler, available_features, available_labels
def test_model(model, scaler, feature_names: List[str], label_names: List[str]):
    """Тестирование на примерах"""
    print("\n" + "=" * 70)
    print("🧪 ТЕСТОВЫЕ СЦЕНАРИИ")
    print("=" * 70)
    
    # Базовые значения
    base_features = {f: 0 for f in feature_names}
    base_features.update({
        "total_income": 80000,
        "total_expenses": 55000,
        "savings_rate": 0.31,
        "expense_to_income_ratio": 0.69,
        "num_transactions": 45,
        "avg_transaction": 1200,
        "median_transaction": 800,
        "max_transaction": 5000,
        "impulse_ratio": 4.0,
        "cv_transaction": 0.6,
        "weekend_ratio": 0.30,
    })
    
    tests = [
        {
            "name": "🧑 Обычный пользователь",
            "features": {},
            "expected_empty": True,
        },
        {
            "name": "🍕 Любитель ресторанов",
            "features": {
                "total_restaurants": 18000,
                "count_restaurants": 15,
                "avg_restaurants": 1200,
                "ratio_income_restaurants": 0.22,
                "weekend_ratio": 0.50,
            },
            "expected": ["high_restaurants"],
        },
        {
            "name": "🛒 Шопоголик",
            "features": {
                "total_shopping": 25000,
                "count_shopping": 12,
                "max_shopping": 15000,
                "impulse_ratio": 8.0,
                "cv_transaction": 1.2,
                "savings_rate": 0.10,
                "expense_to_income_ratio": 0.90,
            },
            "expected": ["high_shopping", "impulse_buyer"],
        },
        {
            "name": "💰 Экономный",
            "features": {
                "savings_rate": 0.40,
                "expense_to_income_ratio": 0.60,
                "impulse_ratio": 2.0,
                "cv_transaction": 0.3,
            },
            "expected_empty": True,
        },
        {
            "name": "🚕 Такси-зависимый",
            "features": {
                "total_transport": 20000,
                "count_transport": 25,
                "avg_transport": 800,
                "ratio_income_transport": 0.25,
            },
            "expected": ["high_transport"],
        },
    ]
    
    for test in tests:
        print(f"\n{test['name']}:")
        
        # Объединяем базовые + тестовые фичи
        row = base_features.copy()
        row.update(test["features"])
        
        X = pd.DataFrame([row])[feature_names]
        X_scaled = scaler.transform(X)
        
        preds = model.predict(X_scaled)[0]
        active = [label_names[i] for i, p in enumerate(preds) if p == 1]
        
        print(f"   Предсказано: {active if active else '(нет меток)'}")
        
        # Проверка
        if test.get("expected_empty"):
            if not active:
                print("   ✅ Верно (ожидалось пусто)")
            else:
                print(f"   ⚠️  Ожидалось пусто")
        elif "expected" in test:
            expected = set(test["expected"])
            got = set(active)
            if expected & got:
                print(f"   ✅ Совпадение: {expected & got}")
            else:
                print(f"   ⚠️  Ожидалось: {expected}")
if __name__ == "__main__":
    model, scaler, features, labels = train()
    test_model(model, scaler, features, labels)