import json
import joblib
import numpy as np
import pandas as pd
import os
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, field


# =============================================================================
# КОНСТАНТЫ
# =============================================================================

EXPENSE_CATEGORIES = [
    "groceries", "restaurants", "transport", "subscriptions",
    "shopping", "utilities", "health", "entertainment", "education"
]

# Бенчмарки (средние доли расходов)
BENCHMARK_SHARES = {
    "groceries": 0.25,
    "restaurants": 0.08,
    "transport": 0.10,
    "subscriptions": 0.04,
    "shopping": 0.12,
    "utilities": 0.12,
    "health": 0.05,
    "entertainment": 0.06,
    "education": 0.03,
}

# Пороги для правил
RULE_THRESHOLDS = {
    "restaurants": {"share": 0.12, "min_total": 3000, "min_count": 4},
    "subscriptions": {"share": 0.06, "min_total": 1000, "min_count": 4},
    "shopping": {"share": 0.18, "min_total": 8000, "min_count": 3},
    "transport": {"share": 0.15, "min_total": 6000, "min_count": 8},
    "entertainment": {"share": 0.10, "min_total": 4000, "min_count": 3},
    "groceries": {"share": 0.35, "min_total": 20000, "min_count": 10},
}


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class Recommendation:
    """Структура рекомендации"""
    title: str
    description: str
    potential_savings: Optional[float] = None
    priority: str = "medium"  # high, medium, low
    category: Optional[str] = None
    source: str = "rule"  # rule, ml


# =============================================================================
# FEATURE EXTRACTOR
# =============================================================================

class FeatureExtractor:
    """Извлечение признаков из транзакций"""
    
    def extract(self, transactions: List[Dict]) -> Dict[str, float]:
        if not transactions:
            return {}
        
        df = pd.DataFrame(transactions)
        
        # Defaults
        for col, default in [("weekend", 0), ("merchant", ""), ("type", "expense"), ("category", "other")]:
            if col not in df.columns:
                df[col] = default
        
        exp = df[df["type"] == "expense"].copy()
        inc = df[df["type"] == "income"].copy()
        
        total_income = inc["amount"].sum() if not inc.empty else 0
        total_expenses = exp["amount"].sum() if not exp.empty else 0
        
        features = {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "savings_rate": (total_income - total_expenses) / total_income if total_income > 0 else 0,
            "expense_to_income_ratio": total_expenses / total_income if total_income > 0 else 1,
        }
        
        # По категориям
        for cat in EXPENSE_CATEGORIES:
            cat_exp = exp[exp["category"] == cat]
            cat_total = cat_exp["amount"].sum() if not cat_exp.empty else 0
            cat_count = len(cat_exp)
            cat_avg = cat_exp["amount"].mean() if not cat_exp.empty else 0
            cat_std = cat_exp["amount"].std() if len(cat_exp) > 1 else 0
            cat_max = cat_exp["amount"].max() if not cat_exp.empty else 0
            
            features[f"total_{cat}"] = cat_total
            features[f"count_{cat}"] = cat_count
            features[f"avg_{cat}"] = cat_avg
            features[f"std_{cat}"] = cat_std
            features[f"max_{cat}"] = cat_max
            features[f"share_{cat}"] = cat_total / total_expenses if total_expenses > 0 else 0
            features[f"ratio_income_{cat}"] = cat_total / total_income if total_income > 0 else 0
        
        # Weekend
        weekend_exp = exp[exp["weekend"] == 1]["amount"].sum() if not exp.empty else 0
        features["weekend_total"] = weekend_exp
        features["weekend_ratio"] = weekend_exp / total_expenses if total_expenses > 0 else 0
        
        # Транзакционные
        if not exp.empty:
            features["num_transactions"] = len(exp)
            features["avg_transaction"] = exp["amount"].mean()
            features["median_transaction"] = exp["amount"].median()
            features["max_transaction"] = exp["amount"].max()
            features["min_transaction"] = exp["amount"].min()
            features["std_transaction"] = exp["amount"].std() if len(exp) > 1 else 0
            features["impulse_ratio"] = features["max_transaction"] / features["median_transaction"] if features["median_transaction"] > 0 else 0
            features["cv_transaction"] = features["std_transaction"] / features["avg_transaction"] if features["avg_transaction"] > 0 else 0
            features["unique_merchants"] = exp["merchant"].nunique()
            features["unique_categories"] = exp["category"].nunique()
            features["tx_per_category"] = features["num_transactions"] / features["unique_categories"] if features["unique_categories"] > 0 else 0
        else:
            for k in ["num_transactions", "avg_transaction", "median_transaction",
                     "max_transaction", "min_transaction", "std_transaction",
                     "impulse_ratio", "cv_transaction", "unique_merchants",
                     "unique_categories", "tx_per_category"]:
                features[k] = 0
        
        # Концентрация (топ-3)
        cat_totals = [(cat, features.get(f"total_{cat}", 0)) for cat in EXPENSE_CATEGORIES]
        cat_totals.sort(key=lambda x: x[1], reverse=True)
        features["top3_concentration"] = sum(t[1] for t in cat_totals[:3]) / total_expenses if total_expenses > 0 else 0
        
        return features


# =============================================================================
# RULE ENGINE
# =============================================================================

class RuleEngine:
    """Генератор рекомендаций на основе правил"""
    
    CATEGORY_RULES = {
        "restaurants": {
            "title": "Сократите расходы на рестораны и кафе",
            "template": "Вы тратите {share:.0f}% бюджета на питание вне дома ({total:,.0f}₽ за {count} визитов). "
                       "Это в {ratio:.1f}x выше среднего. Готовьте дома 3-4 раза в неделю.",
            "savings_pct": 0.35,
        },
        "subscriptions": {
            "title": "Проведите аудит подписок",
            "template": "У вас {count} подписок на {total:,.0f}₽/мес. "
                       "Проверьте каждую — часто 2-3 сервиса дублируют функции.",
            "savings_pct": 0.50,
        },
        "shopping": {
            "title": "Контролируйте импульсивные покупки",
            "template": "На шоппинг уходит {share:.0f}% бюджета ({total:,.0f}₽). "
                       "Правило 48 часов: перед покупкой дороже 3000₽ подождите 2 дня.",
            "savings_pct": 0.30,
        },
        "transport": {
            "title": "Оптимизируйте транспортные расходы",
            "template": "Транспорт съедает {share:.0f}% бюджета ({total:,.0f}₽, {count} поездок). "
                       "Месячный проездной = 5-6 поездок на такси.",
            "savings_pct": 0.35,
        },
        "entertainment": {
            "title": "Установите лимит на развлечения",
            "template": "На развлечения уходит {share:.0f}% ({total:,.0f}₽). "
                       "Установите месячный бюджет и ищите бесплатные альтернативы.",
            "savings_pct": 0.30,
        },
        "groceries": {
            "title": "Оптимизируйте расходы на продукты",
            "template": "Продукты занимают {share:.0f}% бюджета ({total:,.0f}₽). "
                       "Составляйте список, используйте кешбэк и акции.",
            "savings_pct": 0.15,
        },
    }
    
    def generate(self, features: Dict[str, float]) -> List[Recommendation]:
        """Генерирует рекомендации по правилам"""
        recs = []
        total_expenses = features.get("total_expenses", 0)
        total_income = features.get("total_income", 0)
        
        if total_expenses == 0:
            return []
        
        # === 1. Критический уровень расходов ===
        expense_ratio = features.get("expense_to_income_ratio", 1)
        
        if expense_ratio > 0.95 and total_income > 0:
            recs.append(Recommendation(
                title="⚠️ Критический уровень расходов",
                description=f"Вы тратите {expense_ratio*100:.0f}% доходов. "
                           f"Любой непредвиденный расход = долги. Срочно сократите траты на 15%.",
                potential_savings=round(total_expenses * 0.15),
                priority="high",
                source="rule"
            ))
        elif expense_ratio > 0.85 and total_income > 0:
            target = round(total_income * 0.15)
            recs.append(Recommendation(
                title="Начните откладывать деньги",
                description=f"Расходы = {expense_ratio*100:.0f}% доходов. "
                           f"Откладывайте минимум 15% ({target:,.0f}₽) сразу после зарплаты.",
                potential_savings=target,
                priority="medium",
                source="rule"
            ))
        
        # === 2. Категории с превышением ===
        for cat, rule in self.CATEGORY_RULES.items():
            thresholds = RULE_THRESHOLDS.get(cat, {})
            
            share = features.get(f"share_{cat}", 0)
            total = features.get(f"total_{cat}", 0)
            count = features.get(f"count_{cat}", 0)
            
            # ВСЕ условия должны выполниться
            if (share >= thresholds.get("share", 0.15) and
                total >= thresholds.get("min_total", 1000) and
                count >= thresholds.get("min_count", 2)):
                
                benchmark = BENCHMARK_SHARES.get(cat, 0.10)
                ratio = share / benchmark if benchmark > 0 else 1
                savings = round(total * rule["savings_pct"])
                
                if savings < 500:
                    continue
                
                description = rule["template"].format(
                    share=share * 100,
                    total=total,
                    count=count,
                    ratio=ratio
                )
                
                recs.append(Recommendation(
                    title=rule["title"],
                    description=description,
                    potential_savings=savings,
                    priority="high" if ratio > 2.0 else "medium",
                    category=cat,
                    source="rule"
                ))
        
        # === 3. Импульсивные покупки ===
        impulse = features.get("impulse_ratio", 0)
        max_tx = features.get("max_transaction", 0)
        avg_tx = features.get("avg_transaction", 0)
        
        if impulse > 6 and max_tx > 5000:
            recs.append(Recommendation(
                title="Планируйте крупные покупки",
                description=f"Макс. покупка ({max_tx:,.0f}₽) в {impulse:.0f}x больше средней ({avg_tx:,.0f}₽). "
                           f"Сравнивайте цены, ждите скидок.",
                priority="medium",
                source="rule"
            ))
        
        # === 4. Траты в выходные ===
        weekend = features.get("weekend_ratio", 0)
        if weekend > 0.45:
            weekend_total = total_expenses * weekend
            recs.append(Recommendation(
                title="Контролируйте траты в выходные",
                description=f"В выходные уходит {weekend*100:.0f}% бюджета ({weekend_total:,.0f}₽). "
                           f"Планируйте досуг заранее.",
                potential_savings=round(weekend_total * 0.20),
                priority="medium",
                source="rule"
            ))
        
        # === 5. Позитивное ===
        savings_rate = features.get("savings_rate", 0)
        if savings_rate > 0.25 and total_income > 0:
            recs.append(Recommendation(
                title="🎉 Отличная финансовая дисциплина!",
                description=f"Вы сберегаете {savings_rate*100:.0f}% дохода. "
                           f"Рассмотрите инвестирование: ETF, облигации, накопительный счёт.",
                priority="low",
                source="rule"
            ))
        
        return recs


# =============================================================================
# ML ENGINE
# =============================================================================

class MLEngine:
    """ML-компонент для обнаружения паттернов"""
    
    LABEL_RECOMMENDATIONS = {
        "high_restaurants": {
            "title": "ML: Паттерн высоких трат на рестораны",
            "description": "Модель обнаружила устойчивый паттерн повышенных трат на питание вне дома.",
            "category": "restaurants",
        },
        "high_subscriptions": {
            "title": "ML: Много подписок",
            "description": "Модель обнаружила накопление подписок. Проведите ревизию.",
            "category": "subscriptions",
        },
        "high_shopping": {
            "title": "ML: Паттерн импульсивного шоппинга",
            "description": "Модель обнаружила склонность к частым покупкам.",
            "category": "shopping",
        },
        "high_transport": {
            "title": "ML: Высокие транспортные расходы",
            "description": "Модель обнаружила паттерн частых поездок.",
            "category": "transport",
        },
        "high_entertainment": {
            "title": "ML: Много трат на развлечения",
            "description": "Модель обнаружила повышенные траты на досуг.",
            "category": "entertainment",
        },
        "impulse_buyer": {
            "title": "ML: Склонность к импульсивным покупкам",
            "description": "Модель обнаружила паттерн крупных незапланированных трат.",
            "category": None,
        },
        "low_savings": {
            "title": "ML: Низкий уровень сбережений",
            "description": "Модель обнаружила, что почти весь доход уходит на расходы.",
            "category": None,
        },
        "weekend_spender": {
            "title": "ML: Концентрация трат в выходные",
            "description": "Модель обнаружила повышенные траты по выходным.",
            "category": None,
        },
    }
    
    def __init__(self, model_dir: str):
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.label_names = None
        self._load(model_dir)
    
    def _load(self, model_dir: str):
        """Загрузка модели"""
        try:
            model_path = os.path.join(model_dir, "multilabel_model.joblib")
            scaler_path = os.path.join(model_dir, "scaler.joblib")
            features_path = os.path.join(model_dir, "feature_names.joblib")
            labels_path = os.path.join(model_dir, "label_names.joblib")
            
            if all(os.path.exists(p) for p in [model_path, scaler_path, features_path, labels_path]):
                self.model = joblib.load(model_path)
                self.scaler = joblib.load(scaler_path)
                self.feature_names = joblib.load(features_path)
                self.label_names = joblib.load(labels_path)
                print(f"   [ML] Модель загружена: {len(self.label_names)} меток")
        except Exception as e:
            print(f"   [ML] Ошибка загрузки: {e}")
    
    def predict(self, features: Dict[str, float]) -> List[str]:
        """Предсказывает активные метки"""
        if self.model is None:
            return []
        
        try:
            # Собираем вектор фичей
            row = {f: features.get(f, 0) for f in self.feature_names}
            X = pd.DataFrame([row])[self.feature_names].fillna(0)
            X = X.replace([np.inf, -np.inf], 0)
            
            # Масштабирование
            X_scaled = self.scaler.transform(X)
            
            # Предсказание
            preds = self.model.predict(X_scaled)[0]
            
            return [self.label_names[i] for i, p in enumerate(preds) if p == 1]
        except Exception as e:
            print(f"   [ML] Ошибка предсказания: {e}")
            return []
    
    def generate(self, features: Dict[str, float], covered_categories: Set[str]) -> List[Recommendation]:
        """Генерирует рекомендации на основе ML"""
        labels = self.predict(features)
        recs = []
        
        for label in labels:
            info = self.LABEL_RECOMMENDATIONS.get(label, {})
            category = info.get("category")
            
            # Пропускаем если категория уже покрыта правилами
            if category and category in covered_categories:
                continue
            
            # Валидация: есть ли реальные траты
            if category:
                total = features.get(f"total_{category}", 0)
                count = features.get(f"count_{category}", 0)
                if total < 500 or count < 1:
                    continue
            
            recs.append(Recommendation(
                title=info.get("title", label),
                description=info.get("description", ""),
                priority="medium",
                category=category,
                source="ml"
            ))
        
        return recs


# =============================================================================
# HYBRID RECOMMENDER
# =============================================================================

class FinanceRecommender:
    """
    Гибридный рекомендатор v3.0
    
    Приоритет:
    1. Правила (детерминированные, точные)
    2. ML (обнаружение скрытых паттернов)
    """
    
    def __init__(self, model_dir: str = ""):
        self.fe = FeatureExtractor()
        self.rules = RuleEngine()
        self.ml = MLEngine(model_dir) if model_dir else None
    
    def predict(self, transactions: List[Dict]) -> List[Dict]:
        """Генерирует рекомендации"""
        if not transactions:
            return []
        
        # 1. Извлекаем фичи
        features = self.fe.extract(transactions)
        
        if features.get("total_expenses", 0) == 0:
            return []
        
        all_recs: List[Recommendation] = []
        
        # 2. Правила (приоритет)
        rule_recs = self.rules.generate(features)
        all_recs.extend(rule_recs)
        
        # 3. Категории, покрытые правилами
        covered = {r.category for r in rule_recs if r.category}
        
        # 4. ML (дополнение)
        if self.ml:
            ml_recs = self.ml.generate(features, covered)
            all_recs.extend(ml_recs)
        
        # 5. Сортировка
        priority_order = {"high": 0, "medium": 1, "low": 2}
        source_order = {"rule": 0, "ml": 1}
        all_recs.sort(key=lambda r: (priority_order.get(r.priority, 1), source_order.get(r.source, 1)))
        
        # 6. Дедупликация
        seen = set()
        unique = []
        for r in all_recs:
            key = r.title[:40].lower()
            if key not in seen:
                seen.add(key)
                unique.append(r)
        
        # 7. Лимит
        final = unique[:6]
        
        # 8. Конвертация в dict
        return [
            {
                "title": r.title,
                "description": r.description,
                "potential_savings": r.potential_savings,
                "priority": r.priority,
                "category": r.category,
                "source": r.source,
            }
            for r in final
        ]


# =============================================================================
# API
# =============================================================================

def get_recommendations(transactions: List[Dict]) -> List[Dict]:
    """Функция для API"""
    try:
        from .model_loader import registry
        rec = registry.get("recommender")
        if rec:
            return rec.predict(transactions)
    except:
        pass
    
    # Fallback: только правила
    rec = FinanceRecommender()
    return rec.predict(transactions)